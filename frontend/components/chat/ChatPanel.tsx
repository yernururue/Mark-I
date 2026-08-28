"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Bot, Check, ChevronDown, RotateCcw, Send } from "lucide-react";
import RouteState from "@/components/RouteState";
import { useChat } from "@/hooks/useChat";

interface ChatPanelProps { uid: string; }

const SUGGESTED_PROMPTS = [
  "Turn our workspace goal into a concrete assignment",
  "What context do you need before you start?",
  "Explain your current tool and context access",
];

export default function ChatPanel({ uid }: ChatPanelProps) {
  const { agents, selectedAgentIds, messages, loading, sending, error, selectAgents, sendMessage, retryMessage, retryLoad } = useChat(uid);
  const [draft, setDraft] = useState("");
  const [selectorOpen, setSelectorOpen] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (loading) return <RouteState title="Loading workspace chat" />;
  if (agents.length === 0) {
    return <RouteState title="Create an agent to start chatting" message="Chat messages must explicitly address one or more agents." />;
  }

  const selectedAgents = agents.filter((agent) => selectedAgentIds.includes(agent.id));
  const submit = (event?: FormEvent) => {
    event?.preventDefault();
    if (!draft.trim() || sending) return;
    const message = draft;
    setDraft("");
    void sendMessage(message);
  };
  const handleKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault(); submit();
    }
  };
  const toggleAgent = (agentId: string) => {
    const next = selectedAgentIds.includes(agentId)
      ? selectedAgentIds.filter((id) => id !== agentId)
      : [...selectedAgentIds, agentId];
    if (next.length > 0) void selectAgents(next);
  };
  const agentName = (agentId?: string) => agents.find((agent) => agent.id === agentId)?.name ?? "Agent";

  return (
    <section className="chat-panel" aria-label="Workspace agent conversation">
      <header className="chat-header">
        <div className="chat-header__avatar" aria-hidden="true"><Bot size={18} /></div>
        <div><h1>Workspace chat</h1><p>{selectedAgents.map((agent) => agent.name).join(", ")}</p></div>
        <div className="agent-selector">
          <button type="button" className="button button--secondary" aria-expanded={selectorOpen} onClick={() => setSelectorOpen((value) => !value)}>
            {selectedAgents.length === 1 ? selectedAgents[0].name : `${selectedAgents.length} agents`}<ChevronDown size={15} />
          </button>
          {selectorOpen ? (
            <div className="agent-selector__menu">
              <p>Address one agent or a selected group</p>
              {agents.map((agent) => (
                <label key={agent.id}>
                  <input type="checkbox" checked={selectedAgentIds.includes(agent.id)} onChange={() => toggleAgent(agent.id)} />
                  <span><strong>{agent.name}</strong><small>{agent.role}</small></span>
                  {selectedAgentIds.includes(agent.id) ? <Check size={15} /> : null}
                </label>
              ))}
              <Link href="/agents">Manage agents</Link>
            </div>
          ) : null}
        </div>
      </header>

      <div className="message-list" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty__mark" aria-hidden="true">M</div>
            <h2>Give an agent a clear starting point</h2>
            <p>Every reply identifies the responsible agent. Group messages keep each response attributable.</p>
            <div className="chat-suggestions">
              {SUGGESTED_PROMPTS.map((prompt) => <button key={prompt} type="button" onClick={() => void sendMessage(prompt)} disabled={sending}>{prompt}</button>)}
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
              {message.status === "failed" ? <button type="button" onClick={() => retryMessage(message.id)} disabled={sending}><RotateCcw size={13} />Retry</button> : null}
              {message.runId ? <Link href={`/runs/${message.runId}`}>Run details</Link> : null}
            </div>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>

      <form className="chat-composer" onSubmit={submit}>
        {error && messages.length > 0 ? <p className="chat-composer__error" role="alert">{error}</p> : null}
        <div className="chat-composer__field">
          <textarea rows={1} value={draft} onChange={(event) => setDraft(event.target.value)} onKeyDown={handleKeyDown} placeholder={`Message ${selectedAgents.length === 1 ? selectedAgents[0].name : "selected agents"}`} aria-label="Message selected agents" disabled={sending} maxLength={2000} />
          <button type="submit" className="chat-send" disabled={!draft.trim() || sending || selectedAgentIds.length === 0} aria-label="Send message"><Send size={18} /></button>
        </div>
        <p>Enter to send · Shift+Enter for a new line · {draft.length}/2000</p>
      </form>
    </section>
  );
}
