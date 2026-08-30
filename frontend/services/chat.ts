import { appConfig } from "@/lib/config";
import { backendContractUnavailable } from "@/lib/errors";
import { createId } from "@/lib/id";
import {
  decodeConversation,
  decodeConversationList,
  decodeMessage,
  decodeMessageList,
  decodeRunList,
  serializeSendMessageCommand,
} from "@/lib/resource-contracts";
import { decodeAgentList } from "@/lib/agent-contracts";
import type {
  Agent,
  AgentRun,
  Conversation,
  Message,
  SendMessageInput,
} from "@/types/models";
import {
  getLocalAgents,
  getLocalConversations,
  getLocalMessages,
  getLocalRuns,
  saveLocalConversations,
  saveLocalMessages,
  saveLocalRuns,
} from "./adapters/local-store";
import type {
  ConversationRepository,
  MessageRepository,
} from "./repository-contracts";

function localAgentReply(agent: Agent, message: string): string {
  const normalized = message.toLowerCase();
  if (
    agent.template === "mentor" &&
    (normalized.includes("github") || normalized.includes("skill"))
  ) {
    return `${agent.name}: Connect GitHub in Settings, then choose which repositories this agent may use. I’ll attribute observations and decisions to this agent.`;
  }
  if (agent.template === "designer") {
    return `${agent.name}: I can explore a focused direction for that. Give me the audience, the constraint that matters most, and what already exists.`;
  }
  return `${agent.name}: I have the assignment. What output should I produce, and which workspace context may I use?`;
}

function localConversations(uid: string): Conversation[] {
  return decodeConversationList(getLocalConversations(uid));
}

function upsertConversation(uid: string, conversation: Conversation): void {
  const current = localConversations(uid);
  saveLocalConversations(uid, [
    conversation,
    ...current.filter((item) => item.id !== conversation.id),
  ]);
}

const localConversationRepository: ConversationRepository = {
  async getConversations(uid, agentId) {
    const conversations = localConversations(uid);
    return agentId
      ? conversations.filter((conversation) => conversation.agentId === agentId)
      : conversations;
  },

  async getOrCreateConversation(uid, agentId) {
    const existing = localConversations(uid).find(
      (conversation) => conversation.agentId === agentId,
    );
    if (existing) return existing;

    const conversation = decodeConversation({
      id: `agent-conversation-${agentId}`,
      agentId,
      title: "Agent chat",
      updatedAt: new Date().toISOString(),
    });
    upsertConversation(uid, conversation);
    return conversation;
  },
};

const firebaseConversationRepository: ConversationRepository = {
  async getConversations() {
    throw backendContractUnavailable(
      "Agent-specific conversations",
      "an authenticated conversation list endpoint filterable by agentId",
    );
  },

  async getOrCreateConversation() {
    throw backendContractUnavailable(
      "Agent-specific conversations",
      "authenticated conversation list/create/select endpoints keyed by agentId",
    );
  },
};

const localMessageRepository: MessageRepository = {
  async getMessages(uid, conversation) {
    const messages = decodeMessageList(getLocalMessages(uid, conversation.id));
    if (
      messages.some(
        (message) =>
          message.conversationId !== conversation.id ||
          message.agentId !== conversation.agentId,
      )
    ) {
      throw new Error("Stored messages do not belong to the selected agent conversation.");
    }
    return messages;
  },

  async sendMessage(uid, input) {
    serializeSendMessageCommand(input);
    const agents = decodeAgentList(getLocalAgents(uid));
    const agent = agents.find((item) => item.id === input.agentId);
    if (!agent) throw new Error("The selected agent is not available.");

    const existing = decodeMessageList(
      getLocalMessages(uid, input.conversationId),
    );
    if (existing.some((message) => message.agentId !== input.agentId)) {
      throw new Error("Stored messages do not belong to the selected agent.");
    }

    const userMessage = decodeMessage({
      id: input.clientMessageId,
      conversationId: input.conversationId,
      agentId: input.agentId,
      role: "user",
      content: input.message.trim(),
      createdAt: new Date().toISOString(),
      status: "sent",
    });
    const withoutDuplicate = existing.filter(
      (message) => message.id !== input.clientMessageId,
    );
    saveLocalMessages(uid, input.conversationId, [
      ...withoutDuplicate,
      userMessage,
    ]);
    await new Promise((resolve) => window.setTimeout(resolve, 650));

    const currentMessages = decodeMessageList(
      getLocalMessages(uid, input.conversationId),
    );
    if (!currentMessages.some((message) => message.id === userMessage.id)) {
      return [];
    }

    const timestamp = new Date().toISOString();
    const runId = createId("run-chat");
    const response = decodeMessage({
      id: createId("message"),
      conversationId: input.conversationId,
      agentId: agent.id,
      runId,
      role: "agent",
      content: localAgentReply(agent, input.message),
      createdAt: timestamp,
      status: "sent",
    });
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
    const runs = decodeRunList(getLocalRuns(uid));
    saveLocalRuns(uid, [run, ...runs]);
    saveLocalMessages(uid, input.conversationId, [
      ...withoutDuplicate,
      userMessage,
      response,
    ]);
    upsertConversation(
      uid,
      decodeConversation({
        id: input.conversationId,
        agentId: input.agentId,
        title: input.message.slice(0, 48),
        updatedAt: response.createdAt,
      }),
    );
    return [response];
  },
};

const firebaseMessageRepository: MessageRepository = {
  async getMessages() {
    throw backendContractUnavailable(
      "Agent-specific message history",
      "conversation-scoped messages carrying conversationId and agentId",
    );
  },

  async sendMessage() {
    throw backendContractUnavailable(
      "Agent-specific chat",
      "POST /api/v1/chat accepting agentId, conversationId, text, and clientMessageId",
    );
  },
};

const conversationRepository =
  appConfig.dataMode === "local"
    ? localConversationRepository
    : firebaseConversationRepository;
const messageRepository =
  appConfig.dataMode === "local"
    ? localMessageRepository
    : firebaseMessageRepository;

export const chatService = {
  getConversations: conversationRepository.getConversations.bind(
    conversationRepository,
  ),
  getOrCreateConversation: conversationRepository.getOrCreateConversation.bind(
    conversationRepository,
  ),
  getMessages: messageRepository.getMessages.bind(messageRepository),
  sendMessage: messageRepository.sendMessage.bind(messageRepository),

  retryMessage(uid: string, input: SendMessageInput): Promise<Message[]> {
    return messageRepository.sendMessage(uid, input);
  },
};
