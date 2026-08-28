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
  { value: "workspace-goal", label: "Workspace goal" },
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
      <div className="settings-fields">
        <label className="field"><span>Name</span><input value={value.name} onChange={(event) => setValue((current) => ({ ...current, name: event.target.value }))} placeholder="Product designer" /></label>
        <label className="field"><span>Role</span><input value={value.role} onChange={(event) => setValue((current) => ({ ...current, role: event.target.value }))} placeholder="designer" /></label>
      </div>
      <label className="field"><span>Template</span><select value={value.template} onChange={(event) => setValue((current) => ({ ...current, template: event.target.value as CreateAgentInput["template"] }))}><option value="mentor">Mentor</option><option value="designer">Designer</option><option value="custom">Custom</option></select></label>
      <label className="field"><span>Objective</span><textarea rows={2} value={value.objective} onChange={(event) => setValue((current) => ({ ...current, objective: event.target.value }))} /></label>
      <label className="field"><span>Instructions</span><textarea rows={4} value={value.instructions} onChange={(event) => setValue((current) => ({ ...current, instructions: event.target.value }))} /></label>
      <label className="field"><span>Tone</span><select value={value.tone} onChange={(event) => setValue((current) => ({ ...current, tone: event.target.value as CreateAgentInput["tone"] }))}><option value="normal">Normal</option><option value="chill">Chill</option><option value="brutal">Brutal</option><option value="concise">Concise</option></select></label>

      <fieldset className="grant-list">
        <legend>Tool access</legend>
        {TOOL_OPTIONS.map((option) => (
          <label key={option.value}><input type="checkbox" checked={value.toolGrants.includes(option.value)} onChange={() => setValue((current) => ({ ...current, toolGrants: toggleGrant(current.toolGrants, option.value) }))} /><span>{option.label}</span></label>
        ))}
      </fieldset>

      <fieldset className="grant-list">
        <legend>Context access</legend>
        {CONTEXT_OPTIONS.map((option) => (
          <label key={option.value}><input type="checkbox" checked={value.contextGrants.includes(option.value)} onChange={() => setValue((current) => ({ ...current, contextGrants: toggleGrant(current.contextGrants, option.value) }))} /><span>{option.label}</span></label>
        ))}
      </fieldset>

      {validationError ? <p className="form-message form-message--error" role="alert">{validationError}</p> : null}
      <div className="form-actions">
        {onCancel ? <button type="button" className="button button--secondary" onClick={onCancel} disabled={submitting}>Cancel</button> : null}
        <button type="submit" className="button button--primary" disabled={submitting}>{submitting ? "Saving…" : submitLabel}</button>
      </div>
    </form>
  );
}
