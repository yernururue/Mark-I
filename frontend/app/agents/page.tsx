"use client";

import { useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Plus, Settings } from "lucide-react";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import AgentForm from "@/components/agents/AgentForm";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { useAuth } from "@/contexts/AuthContext";
import { useAgentRoster } from "@/hooks/useAgentRoster";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import type { CreateAgentInput } from "@/types/models";

function AgentsContent() {
  const { user } = useAuth();
  const searchParams = useSearchParams();
  const { agents, loading, error, retry } = useAgentRoster(user?.uid);
  const [creating, setCreating] = useState(searchParams.get("create") === "true");
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
    <DashboardShell agents={agents}>
      <div className="page-content agents-page">
      <header className="page-header">
        <div><h1>Agents</h1></div>
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
            return (
              <Link href={`/agents/${agent.id}`} key={agent.id} className="agent-card">
                <strong>{agent.name}</strong>
                <Settings size={16} aria-hidden="true" />
              </Link>
            );
          })}
        </div>
      )}
      </div>
    </DashboardShell>
  );
}

export default function AgentsPage() {
  return <RouteGuard><AgentsContent /></RouteGuard>;
}
