"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { ArrowLeft, Square } from "lucide-react";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import DashboardShell from "@/components/dashboard/DashboardShell";
import { useAuth } from "@/contexts/AuthContext";
import { useAgentRoster } from "@/hooks/useAgentRoster";
import { useRunDetail } from "@/hooks/useRunDetail";
import { runsService } from "@/services/runs";

function RunContent() {
  const params = useParams<{ runId: string }>();
  const { user } = useAuth();
  const { agents, loading: rosterLoading, error: rosterError, retry: retryRoster } = useAgentRoster(user?.uid);
  const { artifacts, loading, error, retry, run } = useRunDetail(
    user?.uid,
    params.runId,
  );

  if (loading || rosterLoading) return <RouteState title="Loading run" />;
  if (error || rosterError) return <RouteState title="Run unavailable" message={error ?? rosterError ?? undefined} onRetry={() => { retry(); retryRoster(); }} />;
  if (!run) return <RouteState title="Run not found" message="This run is not available in the workspace." />;
  const agent = agents.find((item) => item.id === run.agentId) ?? null;
  const canCancel = run.status === "queued" || run.status === "running" || run.status === "waiting-for-user";

  const cancelRun = async () => {
    if (!user) return;
    await runsService.cancelRun(user.uid, run.id);
    retry();
  };

  return (
    <DashboardShell agents={agents} selectedAgentId={agent?.id}>
      <div className="page-content run-page">
      <Link href={agent ? `/agents/${agent.id}` : "/dashboard"} className="back-link"><ArrowLeft size={15} />{agent ? agent.name : "Dashboard"}</Link>
      <header className="page-header"><div><h1>{run.assignment}</h1><p>Owned by {agent?.name ?? "Unknown agent"}</p></div><em className="run-status" data-status={run.status}>{run.status}</em></header>
      {canCancel && user ? <button type="button" className="button button--danger" onClick={() => void cancelRun()}><Square size={14} />Cancel run</button> : null}

      <section className="run-timeline">
        <h2>Timeline</h2>
        <ol>
          <li data-complete><strong>Queued</strong><time>{new Date(run.createdAt).toLocaleString()}</time></li>
          <li data-complete={Boolean(run.startedAt)}><strong>Started</strong><time>{run.startedAt ? new Date(run.startedAt).toLocaleString() : "Waiting"}</time></li>
          <li data-complete={Boolean(run.finishedAt)}><strong>{run.status === "failed" ? "Failed" : run.status === "cancelled" ? "Cancelled" : "Finished"}</strong><time>{run.finishedAt ? new Date(run.finishedAt).toLocaleString() : run.progress ?? "In progress"}</time></li>
        </ol>
      </section>

      <section className="settings-section"><div className="settings-section__heading"><h2>Outputs</h2><p>Every artifact remains attributed to this run and agent.</p></div>{artifacts.length === 0 ? <p className="list-empty">No outputs have been published yet.</p> : artifacts.map((artifact) => <article key={artifact.id} className="run-output"><span>{artifact.type}</span><h3>{artifact.title}</h3><p>{artifact.content}</p></article>)}</section>
      </div>
    </DashboardShell>
  );
}

export default function RunPage() {
  return <RouteGuard><RunContent /></RouteGuard>;
}
