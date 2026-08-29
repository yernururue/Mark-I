"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Activity, Archive, Copy, Pause, Play, Settings2, ShieldCheck } from "lucide-react";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import AgentForm from "@/components/agents/AgentForm";
import AgentStatusBadge from "@/components/agents/AgentStatusBadge";
import DashboardShell from "@/components/dashboard/DashboardShell";
import SettingsScaffold from "@/components/settings/SettingsScaffold";
import { useAuth } from "@/contexts/AuthContext";
import { useAgentRoster } from "@/hooks/useAgentRoster";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import type { CreateAgentInput } from "@/types/models";

const AGENT_SETTINGS_NAV = [
  { id: "agent-general", label: "General", icon: Settings2 },
  { id: "agent-access", label: "Permissions", icon: ShieldCheck },
  { id: "agent-actions", label: "Lifecycle", icon: Activity },
];

function AgentSettingsContent() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const { agents, loading, error, retry } = useAgentRoster(user?.uid);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (loading) return <RouteState title="Loading agent settings" />;
  if (error) return <RouteState title="Settings unavailable" message={error} onRetry={retry} />;

  const agent = agents.find((item) => item.id === params.agentId);
  if (!agent) return <RouteState title="Agent not found" message="This agent may have been archived or removed." />;

  const runAction = async (action: () => Promise<unknown>, success?: string): Promise<boolean> => {
    setSubmitting(true);
    setActionError(null);
    setNotice(null);
    try {
      await action();
      setNotice(success ?? null);
      return true;
    } catch (actionFailure) {
      setActionError(getErrorMessage(actionFailure, "The action could not be completed."));
      return false;
    } finally {
      setSubmitting(false);
    }
  };

  const saveAgent = async (input: CreateAgentInput) => {
    if (!user) return;
    await runAction(() => agentsService.updateAgent(user.uid, agent.id, input), "Changes saved.");
  };

  const archiveAgent = async () => {
    if (!user) return;
    const archived = await runAction(
      () => agentsService.updateAgent(user.uid, agent.id, { status: "archived" }),
      "Agent archived.",
    );
    if (archived) router.replace("/dashboard");
  };

  return (
    <DashboardShell agents={agents} selectedAgentId={agent.id}>
      <SettingsScaffold
        title={<span className="agent-name-with-status">{agent.name}<AgentStatusBadge status={agent.status} /></span>}
        items={AGENT_SETTINGS_NAV}
        closeHref={`/dashboard?agent=${encodeURIComponent(agent.id)}`}
        variant="modal"
      >
        {actionError ? <p className="form-message form-message--error" role="alert">{actionError}</p> : null}
        {notice ? <p className="form-message form-message--success" role="status">{notice}</p> : null}

        <AgentForm
          initialAgent={agent}
          submitting={submitting}
          submitLabel="Save changes"
          onSubmit={saveAgent}
        />

        <section id="agent-actions" className="settings-group" aria-label="Agent actions">
          <div className="settings-card settings-actions-list">
            <button
              type="button"
              className="settings-action"
              disabled={submitting}
              onClick={() => user && void runAction(() => agentsService.duplicateAgent(user.uid, agent.id), "Agent duplicated.")}
            >
              <Copy size={16} />
              <span><strong>Duplicate</strong><small>Create a separate copy</small></span>
            </button>

            <button
              type="button"
              className="settings-action"
              disabled={submitting || agent.status === "archived"}
              onClick={() => user && void runAction(
                () => agentsService.updateAgent(user.uid, agent.id, { status: agent.status === "paused" ? "active" : "paused" }),
                undefined,
              )}
            >
              {agent.status === "paused" ? <Play size={16} /> : <Pause size={16} />}
              <span><strong>{agent.status === "paused" ? "Resume" : "Pause"}</strong><small>Change availability</small></span>
            </button>

            <button type="button" className="settings-action settings-action--danger" disabled={submitting || agent.status === "archived"} onClick={() => void archiveAgent()}>
              <Archive size={16} />
              <span><strong>Archive</strong><small>Remove from the agent rail</small></span>
            </button>
          </div>
        </section>
      </SettingsScaffold>
    </DashboardShell>
  );
}

export default function AgentSettingsPage() {
  return <RouteGuard><AgentSettingsContent /></RouteGuard>;
}
