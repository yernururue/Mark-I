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
  const [selectedAgentIds, setSelectedAgentIds] = useState<string[]>([]);
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
        const initialIds = roster[0] ? [roster[0].id] : [];
        const conversations = await chatService.getConversations(uid, initialIds);
        const activeConversation = conversations[0] ?? null;
        const history = activeConversation ? await chatService.getMessages(uid, activeConversation.id) : [];
        if (cancelled) return;
        const savedAgentIds = activeConversation?.agentIds.filter((id) => roster.some((agent) => agent.id === id)) ?? [];
        setAgents(roster);
        setSelectedAgentIds(savedAgentIds.length > 0 ? savedAgentIds : initialIds);
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

  const selectAgents = useCallback(async (agentIds: string[]) => {
    if (!uid || !conversation || sending || agentIds.length === 0) return;
    const next = agentIds.filter((id) => agents.some((agent) => agent.id === id));
    if (next.length === 0) return;
    setSelectedAgentIds(next);
    setConversation(await chatService.updateRecipients(uid, conversation.id, next));
  }, [agents, conversation, sending, uid]);

  const submitMessage = useCallback(async (message: string, existingMessageId?: string) => {
    const trimmed = message.trim();
    if (!uid || !conversation || !trimmed || sending || selectedAgentIds.length === 0) return;
    const clientMessageId = existingMessageId ?? createId("message");
    const userMessage: Message = {
      id: clientMessageId,
      conversationId: conversation.id,
      agentId: selectedAgentIds.length === 1 ? selectedAgentIds[0] : undefined,
      role: "user",
      content: trimmed,
      createdAt: new Date().toISOString(),
      status: "sending",
    };
    const pending = selectedAgentIds.map((agentId) => pendingAgentMessage(agentId, conversation.id));
    const input: SendMessageInput = {
      agentIds: selectedAgentIds,
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
  }, [conversation, selectedAgentIds, sending, uid]);

  const retryMessage = useCallback((messageId: string) => {
    const failed = messages.find((message) => message.id === messageId && message.status === "failed");
    if (failed) void submitMessage(failed.content, failed.id);
  }, [messages, submitMessage]);

  return {
    agents,
    selectedAgentIds,
    conversation,
    messages,
    loading,
    sending,
    error,
    selectAgents,
    sendMessage: submitMessage,
    retryMessage,
    retryLoad,
  };
}
