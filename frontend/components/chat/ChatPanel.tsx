"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Plus, RotateCcw, Send, Settings } from "lucide-react";
import RouteState from "@/components/RouteState";
import DashboardShell from "@/components/dashboard/DashboardShell";
import AgentStatusBadge from "@/components/agents/AgentStatusBadge";
import { useChat } from "@/hooks/useChat";

interface ChatPanelProps { uid: string; }

const SUGGESTED_PROMPTS = [
  "Turn my goal into a concrete assignment",
  "What context do you need before you start?",
  "Explain your current access",
];

export default function ChatPanel({ uid }: ChatPanelProps) {
  const { agents, selectedAgentId, messages, loading, sending, error, selectAgent, sendMessage, retryMessage, retryLoad } = useChat(uid);
  const searchParams = useSearchParams();
  const router = useRouter();
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  useEffect(() => {
    const requestedAgentId = searchParams.get("agent");
    if (requestedAgentId && agents.some((agent) => agent.id === requestedAgentId) && selectedAgentId !== requestedAgentId) {
      void selectAgent(requestedAgentId);
    }
  }, [agents, searchParams, selectAgent, selectedAgentId]);

  if (loading) return <RouteState title="Loading agents" />;
  if (error && agents.length === 0) return <RouteState title="Chat unavailable" message={error} onRetry={retryLoad} />;

  const selectedAgent = agents.find((agent) => agent.id === selectedAgentId) ?? agents[0];
  const canSend = selectedAgent?.status === "active";
  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!draft.trim() || sending) return;
    const message = draft;
    setDraft("");
    void sendMessage(message);
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      submit();
    }
  };
  const agentName = (agentId?: string) => agents.find((agent) => agent.id === agentId)?.name ?? "Agent";

  return (
    <DashboardShell
      agents={agents}
      selectedAgentId={selectedAgent?.id}
      onSelectAgent={(agentId) => router.replace(`/dashboard?agent=${encodeURIComponent(agentId)}`)}
    >
      <div className="chat-panel">
        <header className="chat-header">
          <div className="agent-name-with-status">
            <h1>{selectedAgent?.name ?? "Chat"}</h1>
            {selectedAgent ? <AgentStatusBadge status={selectedAgent.status} /> : null}
          </div>
          {selectedAgent ? (
            <Link href={`/agents/${selectedAgent.id}`} className="icon-button" aria-label={`Open ${selectedAgent.name} settings`}>
              <Settings size={17} aria-hidden="true" />
            </Link>
          ) : null}
        </header>

        <div className="message-list" aria-live="polite">
          {agents.length === 0 ? (
            <div className="chat-empty">
              <h2>Create your first agent</h2>
              <Link href="/agents?create=true" className="button button--primary">
                <Plus size={17} aria-hidden="true" />
                Create agent
              </Link>
            </div>
          ) : messages.length === 0 ? (
            <div className="chat-empty">
              <div className="agent-name-with-status">
                <h2>Start a conversation with {selectedAgent?.name}</h2>
                {selectedAgent ? <AgentStatusBadge status={selectedAgent.status} /> : null}
              </div>
              <div className="chat-suggestions">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <button key={prompt} type="button" onClick={() => void sendMessage(prompt)} disabled={sending || !canSend}>
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {messages.map((message) => (
            <article key={message.id} className="message" data-role={message.role} data-status={message.status}>
              {message.role === "agent" ? <span className="message__agent">{agentName(message.agentId)}</span> : null}
              <div className="message__content">
                {message.status === "sending" && message.role === "agent" ? (
                  <span className="typing-indicator" aria-label={`${agentName(message.agentId)} is responding`}><i /><i /><i /></span>
                ) : <p>{message.content}</p>}
              </div>
              <div className="message__meta">
                <time dateTime={message.createdAt}>{new Date(message.createdAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</time>
                {message.status === "sending" && message.role === "user" ? <span>Sending</span> : null}
                {message.status === "failed" ? (
                  <button type="button" onClick={() => retryMessage(message.id)} disabled={sending}>
                    <RotateCcw size={13} />Retry
                  </button>
                ) : null}
                {message.runId ? <Link href={`/runs/${message.runId}`}>Run details</Link> : null}
              </div>
            </article>
          ))}
          <div ref={bottomRef} />
        </div>

        {agents.length > 0 ? (
          <form className="chat-composer" onSubmit={submit}>
            {error && messages.length > 0 ? <p className="chat-composer__error" role="alert">{error}</p> : null}
            <div className="chat-composer__field">
              <textarea rows={1} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleKeyDown} placeholder={canSend ? `Message ${selectedAgent?.name ?? "agent"}` : `${selectedAgent?.name ?? "Agent"} is paused`} aria-label="Message agent" disabled={sending || !canSend} maxLength={2000} />
              <button type="submit" className="chat-send" disabled={!draft.trim() || sending || !canSend || !selectedAgentId} aria-label="Send message">
                <Send size={18} />
              </button>
            </div>
          </form>
        ) : null}
      </div>
    </DashboardShell>
  );
}
