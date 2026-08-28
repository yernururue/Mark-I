"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { ArrowLeft, Copy, Pause, Play, Send, Archive } from "lucide-react";
import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import AgentForm from "@/components/agents/AgentForm";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardData } from "@/hooks/useDashboardData";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import { runsService } from "@/services/runs";
import type { CreateAgentInput } from "@/types/models";

function AgentDetailContent() {
  const params = useParams<{ agentId: string }>();
  const router = useRouter();
  const { user } = useAuth();
  const { agents, runs, artifacts, loading, error, retry } = useDashboardData(user?.uid);
  const [editing, setEditing] = useState(false);
  const [assignment, setAssignment] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  if (loading) return <RouteState title="Loading agent" />;
  if (error) return <RouteState title="Agent unavailable" message={error} onRetry={retry} />;
  const agent = agents.find((item) => item.id === params.agentId);
  if (!agent) return <RouteState title="Agent not found" message="This agent may have been archived or removed." />;
  const agentRuns = runs.filter((run) => run.agentId === agent.id);

  const runAction = async (action: () => Promise<unknown>, success: string) => {
    setSubmitting(true); setActionError(null); setNotice(null);
    try { await action(); setNotice(success); } catch (actionFailure) { setActionError(getErrorMessage(actionFailure, "The action could not be completed.")); } finally { setSubmitting(false); }
  };

  const saveAgent = async (input: CreateAgentInput) => {
    if (!user) return;
    await runAction(() => agentsService.updateAgent(user.uid, agent.id, input), "Agent configuration saved.");
    setEditing(false);
  };

  const startAssignment = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user || assignment.trim().length < 5) { setActionError("Describe the assignment before starting a run."); return; }
    void runAction(async () => {
      const run = await runsService.startRun(user.uid, agent.id, assignment);
      setAssignment("");
      router.push(`/runs/${run.id}`);
    }, "Run started.");
  };

  return (
    <div className="page-content agent-detail-page">
      <Link href="/agents" className="back-link"><ArrowLeft size={15} />All agents</Link>
      <header className="agent-detail-header">
        <span className="agent-detail-header__avatar" aria-hidden="true">{agent.name.charAt(0).toUpperCase()}</span>
        <div><h1>{agent.name}</h1><p>{agent.role} · {agent.template} template</p></div>
        <em data-status={agent.status}>{agent.status}</em>
      </header>

      {actionError ? <p className="form-message form-message--error" role="alert">{actionError}</p> : null}
      {notice ? <p className="form-message form-message--success" role="status">{notice}</p> : null}

      <div className="agent-actions">
        <button type="button" className="button button--secondary" onClick={() => setEditing((value) => !value)}>Edit configuration</button>
        <button type="button" className="button button--secondary" disabled={submitting} onClick={() => user && void runAction(() => agentsService.duplicateAgent(user.uid, agent.id), "Agent duplicated.")}><Copy size={15} />Duplicate</button>
        <button type="button" className="button button--secondary" disabled={submitting || agent.status === "archived"} onClick={() => user && void runAction(() => agentsService.updateAgent(user.uid, agent.id, { status: agent.status === "paused" ? "active" : "paused" }), agent.status === "paused" ? "Agent resumed." : "Agent paused.")}>{agent.status === "paused" ? <Play size={15} /> : <Pause size={15} />}{agent.status === "paused" ? "Resume" : "Pause"}</button>
        <button type="button" className="button button--danger" disabled={submitting || agent.status === "archived"} onClick={() => user && void runAction(() => agentsService.updateAgent(user.uid, agent.id, { status: "archived" }), "Agent archived.")}><Archive size={15} />Archive</button>
      </div>

      {editing ? <section className="settings-section"><div className="settings-section__heading"><h2>Edit agent</h2><p>Changes apply to new runs immediately.</p></div><AgentForm initialAgent={agent} submitting={submitting} submitLabel="Save changes" onSubmit={saveAgent} onCancel={() => setEditing(false)} /></section> : null}

      <section className="settings-section assignment-section">
        <div className="settings-section__heading"><h2>Start an assignment</h2><p>This creates an isolated run owned by {agent.name}.</p></div>
        <form onSubmit={startAssignment} className="assignment-form"><textarea rows={3} value={assignment} onChange={(event) => setAssignment(event.target.value)} placeholder="Describe the output you need and any constraints." disabled={agent.status !== "active" || submitting} /><button type="submit" className="button button--primary" disabled={agent.status !== "active" || submitting || !assignment.trim()}><Send size={16} />Start run</button></form>
        {agent.status !== "active" ? <p className="settings-mode-note">Resume this agent before starting a new run.</p> : null}
      </section>

      <div className="agent-detail-grid">
        <section className="workspace-panel"><div className="panel-heading"><h2>Run history</h2></div><div className="run-list">{agentRuns.length === 0 ? <p className="list-empty">No runs yet.</p> : agentRuns.map((run) => <Link key={run.id} href={`/runs/${run.id}`} className="run-row"><span><strong>{run.assignment}</strong><small>{new Date(run.createdAt).toLocaleString()}</small></span><em data-status={run.status}>{run.status}</em></Link>)}</div></section>
        <section className="workspace-panel"><div className="panel-heading"><h2>Access</h2></div><dl className="agent-access"><dt>Tools</dt><dd>{agent.toolGrants.join(", ") || "None"}</dd><dt>Context</dt><dd>{agent.contextGrants.join(", ") || "None"}</dd><dt>Tone</dt><dd>{agent.tone}</dd></dl></section>
        <section className="workspace-panel"><div className="panel-heading"><h2>Outputs</h2></div><div className="artifact-list">{artifacts.filter((artifact) => artifact.agentId === agent.id).length === 0 ? <p className="list-empty">No outputs yet.</p> : artifacts.filter((artifact) => artifact.agentId === agent.id).map((artifact) => <Link key={artifact.id} href={`/runs/${artifact.runId}`} className="artifact-row"><span>{artifact.type}</span><strong>{artifact.title}</strong></Link>)}</div></section>
      </div>
    </div>
  );
}

export default function AgentDetailPage() {
  return <RouteGuard><AppShell><AgentDetailContent /></AppShell></RouteGuard>;
}
