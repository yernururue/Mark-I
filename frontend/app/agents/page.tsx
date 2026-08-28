"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Plus } from "lucide-react";
import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import AgentForm from "@/components/agents/AgentForm";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardData } from "@/hooks/useDashboardData";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import type { CreateAgentInput } from "@/types/models";

function AgentsContent() {
  const { user } = useAuth();
  const { agents, runs, loading, error, retry } = useDashboardData(user?.uid);
  const [creating, setCreating] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  if (loading) return <RouteState title="Loading agents" />;
  if (error) return <RouteState title="Agents unavailable" message={error} onRetry={retry} />;

  const createAgent = async (input: CreateAgentInput) => {
    if (!user) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await agentsService.createAgent(user.uid, input);
      setCreating(false);
    } catch (creationError) {
      setActionError(getErrorMessage(creationError, "The agent could not be created."));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="page-content agents-page">
      <header className="page-header">
        <div><h1>Agents</h1><p>Configure independent roles, instructions, tools, context, and lifecycle.</p></div>
        <button type="button" className="button button--primary" onClick={() => setCreating(true)}><Plus size={17} />Create agent</button>
      </header>

      {actionError ? <p className="form-message form-message--error" role="alert">{actionError}</p> : null}
      {creating ? (
        <section className="settings-section agent-create-section">
          <div className="settings-section__heading"><h2>New agent</h2><p>Start with a template or define a custom specialist.</p></div>
          <AgentForm submitting={submitting} submitLabel="Create agent" onSubmit={createAgent} onCancel={() => setCreating(false)} />
        </section>
      ) : null}

      {agents.length === 0 ? (
        <section className="panel-empty agents-empty"><h2>No agents yet</h2><div><p>Create the first specialist for this workspace.</p><span>Each agent keeps its own identity, grants, runs, and outputs.</span></div></section>
      ) : (
        <div className="agents-list">
          {agents.map((agent) => {
            const agentRuns = runs.filter((run) => run.agentId === agent.id);
            const activeRuns = agentRuns.filter((run) => run.status === "queued" || run.status === "running").length;
            return (
              <Link href={`/agents/${agent.id}`} key={agent.id} className="agent-card">
                <span className="agent-card__avatar" aria-hidden="true">{agent.name.charAt(0).toUpperCase()}</span>
                <span className="agent-card__identity"><strong>{agent.name}</strong><small>{agent.role} · {agent.template}</small></span>
                <span className="agent-card__objective">{agent.objective}</span>
                <span className="agent-card__runs">{activeRuns} active · {agentRuns.length} total</span>
                <em data-status={agent.status}>{agent.status}</em>
                <ArrowRight size={16} aria-hidden="true" />
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function AgentsPage() {
  return <RouteGuard><AppShell><AgentsContent /></AppShell></RouteGuard>;
}
