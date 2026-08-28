"use client";

import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { RotateCcw, Send } from "lucide-react";
import RouteState from "@/components/RouteState";
import { useChat } from "@/hooks/useChat";

interface ChatPanelProps {
  uid: string;
}

const SUGGESTED_PROMPTS = [
  "Help me turn my goal into a two-week plan",
  "What should I connect first?",
  "How will you use my GitHub activity?",
];

export default function ChatPanel({ uid }: ChatPanelProps) {
  const {
    agent,
    messages,
    loading,
    sending,
    error,
    sendMessage,
    retryMessage,
    retryLoad,
  } = useChat(uid);
  const [draft, setDraft] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  if (loading) {
    return <RouteState title="Loading your conversation" />;
  }

  if (!agent) {
    return (
      <RouteState
        title="Mentor chat unavailable"
        message={error ?? "No mentor is available for this account."}
        onRetry={retryLoad}
      />
    );
  }

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

  return (
    <section className="chat-panel" aria-label={`Conversation with ${agent.name}`}>
      <header className="chat-header">
        <div className="chat-header__avatar" aria-hidden="true">M</div>
        <div>
          <h1>{agent.name}</h1>
          <p>{agent.status === "available" ? "Available" : "Currently offline"}</p>
        </div>
      </header>

      <div className="message-list" aria-live="polite">
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="chat-empty__mark" aria-hidden="true">M</div>
            <h2>What are you working through?</h2>
            <p>
              Ask about your learning plan, a skill gap, an upcoming interview, or why Mark-I made a notification decision.
            </p>
            <div className="chat-suggestions">
              {SUGGESTED_PROMPTS.map((prompt) => (
                <button
                  key={prompt}
                  type="button"
                  onClick={() => void sendMessage(prompt)}
                  disabled={sending}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        ) : null}

        {messages.map((message) => (
          <article
            key={message.id}
            className="message"
            data-role={message.role}
            data-status={message.status}
          >
            <div className="message__content">
              {message.status === "sending" && message.role === "assistant" ? (
                <span className="typing-indicator" aria-label="Mark-I is responding">
                  <i /><i /><i />
                </span>
              ) : (
                <p>{message.content}</p>
              )}
            </div>
            <div className="message__meta">
              <time dateTime={message.createdAt}>
                {new Date(message.createdAt).toLocaleTimeString([], {
                  hour: "numeric",
                  minute: "2-digit",
                })}
              </time>
              {message.status === "sending" && message.role === "user" ? <span>Sending</span> : null}
              {message.status === "failed" ? (
                <button type="button" onClick={() => retryMessage(message.id)} disabled={sending}>
                  <RotateCcw size={13} aria-hidden="true" /> Retry
                </button>
              ) : null}
            </div>
          </article>
        ))}
        <div ref={bottomRef} />
      </div>

      <form className="chat-composer" onSubmit={submit}>
        {error && messages.length > 0 ? (
          <p className="chat-composer__error" role="alert">{error}</p>
        ) : null}
        <div className="chat-composer__field">
          <textarea
            rows={1}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={`Message ${agent.name}`}
            aria-label={`Message ${agent.name}`}
            disabled={sending}
          />
          <button
            type="submit"
            className="chat-send"
            disabled={!draft.trim() || sending}
            aria-label="Send message"
          >
            <Send size={18} aria-hidden="true" />
          </button>
        </div>
        <p>Enter to send · Shift+Enter for a new line</p>
      </form>
    </section>
  );
}
