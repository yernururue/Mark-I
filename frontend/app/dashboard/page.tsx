"use client";

import Link from "next/link";
import { ArrowRight, Bot, MessageSquare, Plus } from "lucide-react";
import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import DecisionLog from "@/components/dashboard/DecisionLog";
import ObservationFeed from "@/components/dashboard/ObservationFeed";
import SkillRadar from "@/components/dashboard/SkillRadar";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardData } from "@/hooks/useDashboardData";

function DashboardContent() {
  const { user } = useAuth();
  const { profile, agents, runs, artifacts, observations, decisions, loading, error, retry } =
    useDashboardData(user?.uid);

  if (loading) {
    return <RouteState title="Loading your dashboard" />;
  }

  if (error) {
    return (
      <RouteState
        title="Dashboard unavailable"
        message={error}
        onRetry={retry}
      />
    );
  }

  const displayName = user?.displayName?.split(" ")[0];

  return (
    <div className="page-content dashboard-page">
      <header className="page-header">
        <div>
          <h1>{displayName ? `Good to see you, ${displayName}` : "Your workspace"}</h1>
          <p>{profile?.goal || "Set a workspace goal in Settings."}</p>
        </div>
        <Link href="/agents?create=true" className="button button--primary">
          <Plus size={17} aria-hidden="true" />
          Create agent
        </Link>
      </header>

      <section className="dashboard-status" aria-label="Workspace status">
        <div>
          <span>Active agents</span>
          <strong>{agents.filter((agent) => agent.status === "active").length}</strong>
        </div>
        <div>
          <span>Runs in progress</span>
          <strong>{runs.filter((run) => run.status === "running" || run.status === "queued").length}</strong>
        </div>
        <div>
          <span>Outputs</span>
          <strong>{artifacts.length}</strong>
        </div>
        <Link href="/settings">
          Review settings <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </section>

      {agents.length === 0 ? (
        <section className="getting-started" aria-labelledby="getting-started-title">
          <div>
            <Bot size={21} aria-hidden="true" />
            <h2 id="getting-started-title">Create the first agent in this workspace</h2>
            <p>
              Start from a mentor or designer template, or define a custom specialist with its own instructions and access.
            </p>
          </div>
          <Link href="/agents?create=true" className="button button--secondary">
            Create an agent
          </Link>
        </section>
      ) : null}

      {agents.length > 0 ? (
        <div className="workspace-grid">
          <section className="workspace-panel">
            <div className="panel-heading"><h2>Agents</h2><Link href="/agents">View all</Link></div>
            <div className="agent-roster">
              {agents.slice(0, 4).map((agent) => (
                <Link key={agent.id} href={`/agents/${agent.id}`} className="agent-row">
                  <span className="agent-row__avatar" aria-hidden="true">{agent.name.charAt(0).toUpperCase()}</span>
                  <span><strong>{agent.name}</strong><small>{agent.role}</small></span>
                  <em data-status={agent.status}>{agent.status}</em>
                </Link>
              ))}
            </div>
          </section>

          <section className="workspace-panel">
            <div className="panel-heading"><h2>Recent runs</h2></div>
            <div className="run-list">
              {runs.length === 0 ? <p className="list-empty">No assignments have been started.</p> : runs.slice(0, 5).map((run) => {
                const owner = agents.find((agent) => agent.id === run.agentId);
                return (
                  <Link key={run.id} href={`/runs/${run.id}`} className="run-row">
                    <span><strong>{run.assignment}</strong><small>{owner?.name ?? "Unknown agent"}</small></span>
                    <em data-status={run.status}>{run.status}</em>
                  </Link>
                );
              })}
            </div>
          </section>

          <section className="workspace-panel workspace-panel--outputs">
            <div className="panel-heading"><h2>Latest outputs</h2></div>
            {artifacts.length === 0 ? <p className="list-empty">Completed runs will publish reviewable outputs here.</p> : (
              <div className="artifact-list">
                {artifacts.slice(0, 4).map((artifact) => (
                  <Link key={artifact.id} href={`/runs/${artifact.runId}`} className="artifact-row">
                    <span>{artifact.type}</span><strong>{artifact.title}</strong><ArrowRight size={15} />
                  </Link>
                ))}
              </div>
            )}
          </section>
        </div>
      ) : null}

      <div className="dashboard-grid">
        {agents.some((agent) => agent.template === "mentor") ? <SkillRadar skills={profile?.skills} /> : null}
        <ObservationFeed observations={observations} />
        <DecisionLog decisions={decisions} />
      </div>

      {agents.length > 0 ? (
        <Link href="/chat" className="workspace-chat-link">
          <MessageSquare size={18} aria-hidden="true" />
          <span><strong>Open workspace chat</strong><small>Address one agent or a selected group.</small></span>
          <ArrowRight size={16} aria-hidden="true" />
        </Link>
      ) : null}
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RouteGuard>
      <AppShell>
        <DashboardContent />
      </AppShell>
    </RouteGuard>
  );
}
