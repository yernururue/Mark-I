import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { createId } from "@/lib/id";
import type { AgentRun, Artifact, Handoff } from "@/types/models";
import {
  getLocalArtifacts,
  getLocalHandoffs,
  getLocalRuns,
  saveLocalArtifacts,
  saveLocalHandoffs,
  saveLocalRuns,
} from "./adapters/local-store";

function replaceRun(uid: string, run: AgentRun): void {
  saveLocalRuns(uid, getLocalRuns(uid).map((item) => item.id === run.id ? run : item));
}

function simulateLocalRun(uid: string, runId: string): void {
  window.setTimeout(() => {
    const run = getLocalRuns(uid).find((item) => item.id === runId);
    if (!run || run.status !== "queued") return;
    replaceRun(uid, {
      ...run,
      status: "running",
      progress: "Working through the assignment",
      startedAt: new Date().toISOString(),
    });
  }, 500);

  window.setTimeout(() => {
    const run = getLocalRuns(uid).find((item) => item.id === runId);
    if (!run || run.status !== "running") return;
    const timestamp = new Date().toISOString();
    const artifact: Artifact = {
      id: createId("artifact"),
      agentId: run.agentId,
      runId: run.id,
      type: "report",
      title: run.assignment.slice(0, 72),
      content: "This local preview confirms the complete run and output flow. The connected agent runtime will provide the real result.",
      sharedWithAgentIds: [],
      createdAt: timestamp,
    };
    saveLocalArtifacts(uid, [artifact, ...getLocalArtifacts(uid)]);
    replaceRun(uid, {
      ...run,
      status: "completed",
      progress: "Assignment completed",
      artifactIds: [artifact.id],
      finishedAt: timestamp,
    });
  }, 2600);
}

export const runsService = {
  async getRuns(uid: string, agentId?: string): Promise<AgentRun[]> {
    if (appConfig.dataMode === "local") {
      const runs = getLocalRuns(uid);
      return agentId ? runs.filter((run) => run.agentId === agentId) : runs;
    }
    const query = agentId ? `?agentId=${encodeURIComponent(agentId)}` : "";
    return fetchApi<AgentRun[]>(`/runs${query}`);
  },

  async getRun(uid: string, runId: string): Promise<AgentRun> {
    if (appConfig.dataMode === "local") {
      const run = getLocalRuns(uid).find((item) => item.id === runId);
      if (!run) throw new Error("The selected run could not be found.");
      return run;
    }
    return fetchApi<AgentRun>(`/runs/${encodeURIComponent(runId)}`);
  },

  async startRun(uid: string, agentId: string, assignment: string): Promise<AgentRun> {
    if (appConfig.dataMode === "local") {
      const run: AgentRun = {
        id: createId("run"),
        agentId,
        assignment: assignment.trim(),
        status: "queued",
        progress: "Waiting for an available runtime",
        artifactIds: [],
        createdAt: new Date().toISOString(),
      };
      saveLocalRuns(uid, [run, ...getLocalRuns(uid)]);
      simulateLocalRun(uid, run.id);
      return run;
    }
    return fetchApi<AgentRun>(`/agents/${encodeURIComponent(agentId)}/runs`, {
      method: "POST",
      body: JSON.stringify({ assignment: assignment.trim(), inputArtifactIds: [] }),
    });
  },

  async cancelRun(uid: string, runId: string): Promise<AgentRun> {
    if (appConfig.dataMode === "local") {
      const run = await this.getRun(uid, runId);
      if (run.status !== "queued" && run.status !== "running" && run.status !== "waiting-for-user") {
        return run;
      }
      const cancelled: AgentRun = {
        ...run,
        status: "cancelled",
        progress: "Cancelled by the user",
        finishedAt: new Date().toISOString(),
      };
      replaceRun(uid, cancelled);
      return cancelled;
    }
    return fetchApi<AgentRun>(`/runs/${encodeURIComponent(runId)}/cancel`, { method: "POST" });
  },

  async getArtifact(uid: string, artifactId: string): Promise<Artifact> {
    if (appConfig.dataMode === "local") {
      const artifact = getLocalArtifacts(uid).find((item) => item.id === artifactId);
      if (!artifact) throw new Error("The selected output could not be found.");
      return artifact;
    }
    return fetchApi<Artifact>(`/artifacts/${encodeURIComponent(artifactId)}`);
  },

  async updateHandoff(uid: string, handoffId: string, action: "approve" | "reject"): Promise<Handoff> {
    if (appConfig.dataMode === "local") {
      const handoffs = getLocalHandoffs(uid);
      const current = handoffs.find((item) => item.id === handoffId);
      if (!current) throw new Error("The handoff request could not be found.");
      const next: Handoff = { ...current, status: action === "approve" ? "approved" : "rejected" };
      saveLocalHandoffs(uid, handoffs.map((item) => item.id === handoffId ? next : item));
      return next;
    }
    return fetchApi<Handoff>(`/handoffs/${encodeURIComponent(handoffId)}/${action}`, { method: "POST" });
  },
};
