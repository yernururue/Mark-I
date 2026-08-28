"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { createId } from "@/lib/id";
import { agentsService } from "@/services/agents";
import { chatService } from "@/services/chat";
import type {
  Agent,
  Conversation,
  Message,
  SendMessageInput,
} from "@/types/models";

function pendingAssistantMessage(
  agentId: string,
  conversationId: string,
): Message {
  return {
    id: createId("pending"),
    agentId,
    conversationId,
    role: "assistant",
    content: "",
    createdAt: new Date().toISOString(),
    status: "sending",
  };
}

export function useChat(uid: string | undefined) {
  const [agent, setAgent] = useState<Agent | null>(null);
  const [conversation, setConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const retryLoad = useCallback(() => {
    setLoading(true);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (!uid) return;

    let cancelled = false;

    const load = async () => {
      try {
        const [agents, conversations] = await Promise.all([
          agentsService.getAgents(),
          chatService.getConversations(uid),
        ]);
        const activeAgent = agents[0];
        const activeConversation = conversations[0];

        if (!activeAgent || !activeConversation) {
          throw new Error("No mentor conversation is available.");
        }

        const history = await chatService.getMessages(uid, activeConversation.id);
        if (cancelled) return;

        setAgent(activeAgent);
        setConversation(activeConversation);
        setMessages(history);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(getErrorMessage(loadError, "The conversation could not be loaded."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [revision, uid]);

  const submitMessage = useCallback(
    async (message: string, existingMessageId?: string) => {
      const trimmed = message.trim();
      if (!uid || !agent || !conversation || !trimmed || sending) return;

      const clientMessageId = existingMessageId ?? createId("message");
      const userMessage: Message = {
        id: clientMessageId,
        agentId: agent.id,
        conversationId: conversation.id,
        role: "user",
        content: trimmed,
        createdAt: new Date().toISOString(),
        status: "sending",
      };
      const pending = pendingAssistantMessage(agent.id, conversation.id);
      const input: SendMessageInput = {
        agentId: agent.id,
        conversationId: conversation.id,
        message: trimmed,
        clientMessageId,
      };

      setSending(true);
      setError(null);
      setMessages((current) => [
        ...current.filter(
          (item) => item.id !== clientMessageId && !item.id.startsWith("pending-"),
        ),
        userMessage,
        pending,
      ]);

      try {
        const assistantMessage = existingMessageId
          ? await chatService.retryMessage(uid, input)
          : await chatService.sendMessage(uid, input);
        setMessages((current) => [
          ...current
            .filter((item) => item.id !== pending.id)
            .map((item) =>
              item.id === clientMessageId ? { ...item, status: "sent" as const } : item,
            ),
          assistantMessage,
        ]);
      } catch (sendError) {
        const messageText = getErrorMessage(
          sendError,
          "The message could not be sent.",
        );
        setError(messageText);
        setMessages((current) =>
          current
            .filter((item) => item.id !== pending.id)
            .map((item) =>
              item.id === clientMessageId
                ? { ...item, status: "failed" as const, error: messageText }
                : item,
            ),
        );
      } finally {
        setSending(false);
      }
    },
    [agent, conversation, sending, uid],
  );

  const retryMessage = useCallback(
    (messageId: string) => {
      const failedMessage = messages.find(
        (message) => message.id === messageId && message.status === "failed",
      );
      if (failedMessage) {
        void submitMessage(failedMessage.content, failedMessage.id);
      }
    },
    [messages, submitMessage],
  );

  return {
    agent,
    conversation,
    messages,
    loading,
    sending,
    error,
    sendMessage: submitMessage,
    retryMessage,
    retryLoad,
  };
}
