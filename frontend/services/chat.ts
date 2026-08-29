import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { AppError } from "@/lib/errors";
import { createId } from "@/lib/id";
import type { Agent, AgentRun, Conversation, Message, SendMessageInput } from "@/types/models";
import { getLocalAgents, getLocalConversations, getLocalMessages, getLocalRuns, saveLocalConversations, saveLocalMessages, saveLocalRuns } from "./adapters/local-store";

interface ApiMessagesResponse {
  messages: Array<{
    id: string;
    role: "user" | "agent";
    agentId?: string;
    runId?: string;
    text: string;
    createdAt: string;
  }>;
}

function localAgentReply(agent: Agent, message: string): string {
  const normalized = message.toLowerCase();
  if (agent.template === "mentor" && (normalized.includes("github") || normalized.includes("skill"))) {
    return `${agent.name}: Connect GitHub in Settings, then choose which repositories this agent may use. I’ll attribute observations and decisions to this agent.`;
  }
  if (agent.template === "designer") {
    return `${agent.name}: I can explore a focused direction for that. Give me the audience, the constraint that matters most, and what already exists.`;
  }
  return `${agent.name}: I have the assignment. What output should I produce, and which workspace context may I use?`;
}

function upsertConversation(uid: string, conversation: Conversation): void {
  const current = getLocalConversations(uid);
  saveLocalConversations(uid, [conversation, ...current.filter((item) => item.id !== conversation.id)]);
}

function getOrCreateLocalConversation(uid: string, agentId: string): Conversation {
  const existing = getLocalConversations(uid).find(
    (conversation) => conversation.agentId === agentId,
  );
  if (existing) return existing;

  const conversation: Conversation = {
    id: `agent-conversation-${agentId}`,
    agentId,
    title: "Agent chat",
    updatedAt: new Date().toISOString(),
  };
  upsertConversation(uid, conversation);
  return conversation;
}

function unavailableRemoteConversation(): never {
  throw new AppError(
    "Agent-specific conversations require the backend conversation endpoints before remote chat can be used.",
    "backend-contract",
  );
}

export const chatService = {
  async getOrCreateConversation(
    uid: string,
    agentId: string,
  ): Promise<Conversation> {
    if (appConfig.dataMode === "local") {
      return getOrCreateLocalConversation(uid, agentId);
    }

    return unavailableRemoteConversation();
  },

  async getMessages(uid: string, conversationId: string): Promise<Message[]> {
    if (appConfig.dataMode === "local") return getLocalMessages(uid, conversationId);
    const response = await fetchApi<ApiMessagesResponse>("/messages?limit=100&channel=web");
    return response.messages.map((message) => ({
      id: message.id,
      conversationId,
      agentId: message.agentId,
      runId: message.runId,
      role: message.role,
      content: message.text,
      createdAt: message.createdAt,
      status: "sent",
    }));
  },

  async sendMessage(uid: string, input: SendMessageInput): Promise<Message[]> {
    if (appConfig.dataMode !== "local") return unavailableRemoteConversation();

    const agent = getLocalAgents(uid).find((item) => item.id === input.agentId);
    if (!agent) throw new Error("The selected agent is not available.");
    const existing = getLocalMessages(uid, input.conversationId);
    const userMessage: Message = {
      id: input.clientMessageId,
      conversationId: input.conversationId,
      agentId: input.agentId,
      role: "user",
      content: input.message,
      createdAt: new Date().toISOString(),
      status: "sent",
    };
    const withoutDuplicate = existing.filter((message) => message.id !== input.clientMessageId);
    saveLocalMessages(uid, input.conversationId, [...withoutDuplicate, userMessage]);
    await new Promise((resolve) => window.setTimeout(resolve, 650));

    const timestamp = new Date().toISOString();
    const runId = createId("run-chat");
    const response: Message = {
      id: createId("message"),
      conversationId: input.conversationId,
      agentId: agent.id,
      runId,
      role: "agent",
      content: localAgentReply(agent, input.message),
      createdAt: timestamp,
      status: "sent",
    };
    const run: AgentRun = {
      id: runId,
      agentId: agent.id,
      assignment: `Chat: ${input.message}`,
      status: "completed",
      progress: "Response delivered in agent chat",
      artifactIds: [],
      createdAt: timestamp,
      startedAt: timestamp,
      finishedAt: timestamp,
    };
    saveLocalRuns(uid, [run, ...getLocalRuns(uid)]);
    const responses = [response];
    saveLocalMessages(uid, input.conversationId, [...withoutDuplicate, userMessage, ...responses]);
    upsertConversation(uid, {
      id: input.conversationId,
      agentId: input.agentId,
      title: input.message.slice(0, 48),
      updatedAt: response.createdAt,
    });
    return responses;
  },

  retryMessage(uid: string, input: SendMessageInput): Promise<Message[]> {
    return this.sendMessage(uid, input);
  },
};
