"use client";

import { useState, type FormEvent } from "react";
import type { Agent, CreateAgentInput } from "@/types/models";

const TOOL_OPTIONS = [
  { value: "read_workspace", label: "Read shared workspace" },
  { value: "query_github", label: "Query connected GitHub repositories" },
  { value: "search_opportunities", label: "Search opportunity sources" },
  { value: "publish_artifact", label: "Publish outputs" },
];

const CONTEXT_OPTIONS = [
  { value: "workspace-goal", label: "Shared goal" },
  { value: "github-activity", label: "GitHub activity" },
  { value: "product-brief", label: "Product brief" },
];

const EMPTY_AGENT: CreateAgentInput = {
  name: "",
  role: "",
  template: "custom",
  objective: "",
  instructions: "",
  tone: "normal",
  toolGrants: ["read_workspace", "publish_artifact"],
  contextGrants: ["workspace-goal"],
};

interface AgentFormProps {
  initialAgent?: Agent;
  submitting: boolean;
  submitLabel: string;
  onSubmit: (input: CreateAgentInput) => Promise<void>;
  onCancel?: () => void;
}

function toggleGrant(current: string[], value: string): string[] {
  return current.includes(value)
    ? current.filter((item) => item !== value)
    : [...current, value];
}

export default function AgentForm({ initialAgent, submitting, submitLabel, onSubmit, onCancel }: AgentFormProps) {
  const [value, setValue] = useState<CreateAgentInput>(initialAgent ? {
    name: initialAgent.name,
    role: initialAgent.role,
    template: initialAgent.template,
    objective: initialAgent.objective,
    instructions: initialAgent.instructions,
    tone: initialAgent.tone,
    toolGrants: [...initialAgent.toolGrants],
    contextGrants: [...initialAgent.contextGrants],
  } : EMPTY_AGENT);
  const [validationError, setValidationError] = useState<string | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (value.name.trim().length < 2 || value.role.trim().length < 2 || value.objective.trim().length < 10 || value.instructions.trim().length < 10) {
      setValidationError("Add a name, role, objective, and clear instructions.");
      return;
    }
    setValidationError(null);
    void onSubmit({
      ...value,
      name: value.name.trim(),
      role: value.role.trim(),
      objective: value.objective.trim(),
      instructions: value.instructions.trim(),
    });
  };

  return (
    <form className="agent-form form-stack" onSubmit={submit}>
      <section id="agent-general" className="settings-group" aria-label="Agent configuration">
        <div className="settings-card settings-rows">
          <div className="settings-row">
            <label>Name</label>
            <input value={value.name} onChange={(event) => setValue((current) => ({ ...current, name: event.target.value }))} placeholder="Product designer" />
          </div>
          <div className="settings-row">
            <label>Role</label>
            <input value={value.role} onChange={(event) => setValue((current) => ({ ...current, role: event.target.value }))} placeholder="designer" />
          </div>
          <div className="settings-row">
            <label>Template</label>
            <select value={value.template} onChange={(event) => setValue((current) => ({ ...current, template: event.target.value as CreateAgentInput["template"] }))}><option value="mentor">Mentor</option><option value="designer">Designer</option><option value="custom">Custom</option></select>
          </div>
          <div className="settings-row">
            <label>Tone</label>
            <select value={value.tone} onChange={(event) => setValue((current) => ({ ...current, tone: event.target.value as CreateAgentInput["tone"] }))}><option value="normal">Normal</option><option value="chill">Chill</option><option value="brutal">Brutal</option><option value="concise">Concise</option></select>
          </div>
        </div>

        <div className="settings-card settings-rows" style={{ marginTop: "1rem" }}>
          <div className="settings-row" style={{flexDirection: "column", alignItems: "stretch", gap: "0.75rem"}}>
            <label>Objective</label>
            <textarea rows={2} value={value.objective} onChange={(event) => setValue((current) => ({ ...current, objective: event.target.value }))} />
          </div>
          <div className="settings-row" style={{flexDirection: "column", alignItems: "stretch", gap: "0.75rem"}}>
            <label>Instructions</label>
            <textarea rows={4} value={value.instructions} onChange={(event) => setValue((current) => ({ ...current, instructions: event.target.value }))} />
          </div>
        </div>
      </section>

      <section id="agent-access" className="settings-group" aria-label="Agent permissions">
        <div className="settings-card settings-rows">
          <div className="settings-row" style={{flexDirection: "column", alignItems: "stretch", gap: "0.75rem"}}>
            <label style={{ color: "var(--text-secondary)", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Tool Permissions</label>
            <div className="grant-list" style={{ borderTop: "none", paddingTop: 0, gap: "0.75rem" }}>
              {TOOL_OPTIONS.map((option) => (
                <label key={option.value} className="choice-row"><input type="checkbox" checked={value.toolGrants.includes(option.value)} onChange={() => setValue((current) => ({ ...current, toolGrants: toggleGrant(current.toolGrants, option.value) }))} /><span>{option.label}</span></label>
              ))}
            </div>
          </div>

          <div className="settings-row" style={{flexDirection: "column", alignItems: "stretch", gap: "0.75rem"}}>
            <label style={{ color: "var(--text-secondary)", fontSize: "0.8rem", textTransform: "uppercase", letterSpacing: "0.05em" }}>Context Permissions</label>
            <div className="grant-list" style={{ borderTop: "none", paddingTop: 0, gap: "0.75rem" }}>
              {CONTEXT_OPTIONS.map((option) => (
                <label key={option.value} className="choice-row"><input type="checkbox" checked={value.contextGrants.includes(option.value)} onChange={() => setValue((current) => ({ ...current, contextGrants: toggleGrant(current.contextGrants, option.value) }))} /><span>{option.label}</span></label>
              ))}
            </div>
          </div>
        </div>
      </section>

      {validationError ? <p className="form-message form-message--error" role="alert">{validationError}</p> : null}
      <div className="form-actions" style={{ padding: "0.5rem 0" }}>
        {onCancel ? <button type="button" className="button button--secondary" onClick={onCancel} disabled={submitting}>Cancel</button> : null}
        <button type="submit" className="button button--primary" disabled={submitting}>{submitting ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}
