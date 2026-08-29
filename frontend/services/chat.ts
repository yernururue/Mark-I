import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { createId } from "@/lib/id";
import type { Agent, AgentRun, Conversation, Message, SendMessageInput } from "@/types/models";
import { getLocalAgents, getLocalConversations, getLocalMessages, getLocalRuns, saveLocalConversations, saveLocalMessages, saveLocalRuns } from "./adapters/local-store";

interface ApiChatResponse {
  agentId: string;
  runId: string;
  response: string;
  agentMessageId: string;
}

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

export const chatService = {
  async getConversations(uid: string, agentIds: string[]): Promise<Conversation[]> {
    if (appConfig.dataMode !== "local") {
      return [{ id: "workspace-chat", agentIds, title: "Workspace chat", updatedAt: new Date().toISOString() }];
    }
    const conversations = getLocalConversations(uid);
    if (conversations.length > 0) return conversations;
    const primary: Conversation = {
      id: "workspace-chat",
      agentIds,
      title: "Workspace chat",
      updatedAt: new Date().toISOString(),
    };
    saveLocalConversations(uid, [primary]);
    return [primary];
  },

  async updateRecipients(uid: string, conversationId: string, agentIds: string[]): Promise<Conversation> {
    const existing = (await this.getConversations(uid, agentIds)).find((item) => item.id === conversationId);
    const conversation: Conversation = {
      id: conversationId,
      title: agentIds.length > 1 ? "Agent group" : "Agent chat",
      updatedAt: new Date().toISOString(),
      ...existing,
      agentIds,
    };
    if (appConfig.dataMode === "local") upsertConversation(uid, conversation);
    return conversation;
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
    if (appConfig.dataMode !== "local") {
      const response = await fetchApi<ApiChatResponse>("/chat", {
        method: "POST",
        body: JSON.stringify({ agentIds: input.agentIds, message: input.message, channel: "web" }),
      });
      return [{
        id: response.agentMessageId,
        conversationId: input.conversationId,
        agentId: response.agentId,
        runId: response.runId,
        role: "agent",
        content: response.response,
        createdAt: new Date().toISOString(),
        status: "sent",
      }];
    }

    const agents = getLocalAgents(uid).filter((agent) => input.agentIds.includes(agent.id));
    if (agents.length === 0) throw new Error("Select at least one active agent.");
    const existing = getLocalMessages(uid, input.conversationId);
    const userMessage: Message = {
      id: input.clientMessageId,
      conversationId: input.conversationId,
      agentId: input.agentIds.length === 1 ? input.agentIds[0] : undefined,
      role: "user",
      content: input.message,
      createdAt: new Date().toISOString(),
      status: "sent",
    };
    const withoutDuplicate = existing.filter((message) => message.id !== input.clientMessageId);
    saveLocalMessages(uid, input.conversationId, [...withoutDuplicate, userMessage]);
    await new Promise((resolve) => window.setTimeout(resolve, 650));

    const timestamp = new Date().toISOString();
    const responsePairs = agents.map((agent) => {
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
        progress: "Response delivered in workspace chat",
        artifactIds: [],
        createdAt: timestamp,
        startedAt: timestamp,
        finishedAt: timestamp,
      };
      return { response, run };
    });
    const responses = responsePairs.map((pair) => pair.response);
    saveLocalRuns(uid, [...responsePairs.map((pair) => pair.run), ...getLocalRuns(uid)]);
    saveLocalMessages(uid, input.conversationId, [...withoutDuplicate, userMessage, ...responses]);
    upsertConversation(uid, {
      id: input.conversationId,
      agentIds: input.agentIds,
      title: input.message.slice(0, 48),
      updatedAt: responses.at(-1)?.createdAt ?? userMessage.createdAt,
    });
    return responses;
  },

  retryMessage(uid: string, input: SendMessageInput): Promise<Message[]> {
    return this.sendMessage(uid, input);
  },
};
