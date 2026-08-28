import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { createId } from "@/lib/id";
import type {
  Conversation,
  Message,
  SendMessageInput,
} from "@/types/models";
import {
  getLocalConversations,
  getLocalMessages,
  saveLocalConversations,
  saveLocalMessages,
} from "./adapters/local-store";

const PRIMARY_CONVERSATION_ID = "primary";

function createPrimaryConversation(): Conversation {
  return {
    id: PRIMARY_CONVERSATION_ID,
    agentId: "mark-i-mentor",
    title: "Growth mentoring",
    updatedAt: new Date().toISOString(),
  };
}

function localAssistantReply(message: string): string {
  const normalized = message.toLowerCase();

  if (normalized.includes("github") || normalized.includes("repo")) {
    return "Connect GitHub in Settings and choose the repositories you want me to watch. Once the backend is connected, I’ll use that activity to track your skills and explain what changed.";
  }

  if (normalized.includes("job") || normalized.includes("interview")) {
    return "I can help turn that into a focused plan. Tell me the role you’re targeting and the strongest project you can show today, and we’ll identify the highest-impact gap first.";
  }

  if (normalized.includes("learn") || normalized.includes("skill")) {
    return "Let’s make the goal measurable. What should you be able to build or explain confidently in the next two weeks?";
  }

  return "I’ve got it. What outcome would make this feel like meaningful progress, and what is blocking you right now?";
}

function upsertConversation(uid: string, conversation: Conversation): void {
  const conversations = getLocalConversations(uid);
  const next = [
    conversation,
    ...conversations.filter((item) => item.id !== conversation.id),
  ];
  saveLocalConversations(uid, next);
}

export const chatService = {
  async getConversations(uid: string): Promise<Conversation[]> {
    if (appConfig.dataMode !== "local") {
      return fetchApi<Conversation[]>("/conversations");
    }

    const conversations = getLocalConversations(uid);
    if (conversations.length > 0) return conversations;

    const primary = createPrimaryConversation();
    saveLocalConversations(uid, [primary]);
    return [primary];
  },

  async getConversation(uid: string, conversationId: string): Promise<Conversation> {
    const conversations = await this.getConversations(uid);
    const conversation = conversations.find((item) => item.id === conversationId);

    if (!conversation) {
      throw new Error("The conversation could not be found.");
    }

    return conversation;
  },

  async createConversation(uid: string, agentId: string): Promise<Conversation> {
    if (appConfig.dataMode !== "local") {
      return fetchApi<Conversation>("/conversations", {
        method: "POST",
        body: JSON.stringify({ agentId }),
      });
    }

    const conversation: Conversation = {
      id: createId("conversation"),
      agentId,
      title: "New conversation",
      updatedAt: new Date().toISOString(),
    };
    upsertConversation(uid, conversation);
    return conversation;
  },

  async getMessages(uid: string, conversationId: string): Promise<Message[]> {
    if (appConfig.dataMode !== "local") {
      return fetchApi<Message[]>(
        `/conversations/${encodeURIComponent(conversationId)}/messages`,
      );
    }

    return getLocalMessages(uid, conversationId);
  },

  async sendMessage(
    uid: string,
    input: SendMessageInput,
  ): Promise<Message> {
    if (appConfig.dataMode !== "local") {
      return fetchApi<Message>("/chat", {
        method: "POST",
        body: JSON.stringify(input),
      });
    }

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
    const withoutDuplicate = existing.filter(
      (message) => message.id !== input.clientMessageId,
    );
    saveLocalMessages(uid, input.conversationId, [
      ...withoutDuplicate,
      userMessage,
    ]);

    await new Promise((resolve) => window.setTimeout(resolve, 650));

    const assistantMessage: Message = {
      id: createId("message"),
      conversationId: input.conversationId,
      agentId: input.agentId,
      role: "assistant",
      content: localAssistantReply(input.message),
      createdAt: new Date().toISOString(),
      status: "sent",
    };
    saveLocalMessages(uid, input.conversationId, [
      ...withoutDuplicate,
      userMessage,
      assistantMessage,
    ]);
    upsertConversation(uid, {
      id: input.conversationId,
      agentId: input.agentId,
      title: input.message.slice(0, 48),
      updatedAt: assistantMessage.createdAt,
    });
    return assistantMessage;
  },

  retryMessage(uid: string, input: SendMessageInput): Promise<Message> {
    return this.sendMessage(uid, input);
  },
};
