"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { createId } from "@/lib/id";
import { agentsService } from "@/services/agents";
import { chatService } from "@/services/chat";
import type { Agent, Conversation, Message, SendMessageInput } from "@/types/models";

function pendingAgentMessage(agentId: string, conversationId: string): Message {
  return {
    id: createId("pending"),
    agentId,
    conversationId,
    role: "agent",
    content: "",
    createdAt: new Date().toISOString(),
    status: "sending",
  };
}

export function useChat(uid: string | undefined) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string | null>(null);
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
        const roster = (await agentsService.getAgents(uid)).filter((agent) => agent.status !== "archived");
        const initialAgentId = roster[0]?.id;
        const activeConversation = initialAgentId
          ? await chatService.getOrCreateConversation(uid, initialAgentId)
          : null;
        const history = activeConversation
          ? await chatService.getMessages(uid, activeConversation)
          : [];
        if (cancelled) return;
        setAgents(roster);
        setSelectedAgentId(activeConversation?.agentId ?? null);
        setConversation(activeConversation);
        setMessages(history);
        setError(null);
      } catch (loadError) {
        if (!cancelled) setError(getErrorMessage(loadError, "The conversation could not be loaded."));
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void load();
    return () => { cancelled = true; };
  }, [revision, uid]);

  const selectAgent = useCallback(async (agentId: string) => {
    if (!uid || sending || !agents.some((agent) => agent.id === agentId)) return;

    setLoading(true);
    setError(null);
    try {
      const nextConversation = await chatService.getOrCreateConversation(uid, agentId);
      const nextMessages = await chatService.getMessages(uid, nextConversation);
      setSelectedAgentId(agentId);
      setConversation(nextConversation);
      setMessages(nextMessages);
    } catch (selectionError) {
      setError(getErrorMessage(selectionError, "The agent conversation could not be loaded."));
    } finally {
      setLoading(false);
    }
  }, [agents, sending, uid]);

  const submitMessage = useCallback(async (message: string, existingMessageId?: string) => {
    const trimmed = message.trim();
    if (!uid || !conversation || !trimmed || sending || !selectedAgentId) return;
    const clientMessageId = existingMessageId ?? createId("message");
    const userMessage: Message = {
      id: clientMessageId,
      conversationId: conversation.id,
      agentId: selectedAgentId,
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
      status: "sending",
    };
    const pending = [pendingAgentMessage(selectedAgentId, conversation.id)];
    const input: SendMessageInput = {
      agentId: selectedAgentId,
      conversationId: conversation.id,
      message: trimmed,
      clientMessageId,
    };
    setSending(true);
    setError(null);
    setMessages((current) => [
      ...current.filter((item) => item.id !== clientMessageId && !item.id.startsWith("pending-")),
      userMessage,
      ...pending,
    ]);
    try {
      const responses = existingMessageId
        ? await chatService.retryMessage(uid, input)
        : await chatService.sendMessage(uid, input);
      const pendingIds = new Set(pending.map((item) => item.id));
      setMessages((current) => [
        ...current.filter((item) => !pendingIds.has(item.id)).map((item) => item.id === clientMessageId ? { ...item, status: "sent" as const } : item),
        ...responses,
      ]);
    } catch (sendError) {
      const messageText = getErrorMessage(sendError, "The message could not be sent.");
      const pendingIds = new Set(pending.map((item) => item.id));
      setError(messageText);
      setMessages((current) => current.filter((item) => !pendingIds.has(item.id)).map((item) => item.id === clientMessageId ? { ...item, status: "failed" as const, error: messageText } : item));
    } finally {
      setSending(false);
    }
  }, [conversation, selectedAgentId, sending, uid]);

  const retryMessage = useCallback((messageId: string) => {
    const failed = messages.find((message) => message.id === messageId && message.status === "failed");
    if (failed) void submitMessage(failed.content, failed.id);
  }, [messages, submitMessage]);

  return {
    agents,
    selectedAgentId,
    conversation,
    messages,
    loading,
    sending,
    error,
    selectAgent,
    sendMessage: submitMessage,
    retryMessage,
    retryLoad,
  };
}
