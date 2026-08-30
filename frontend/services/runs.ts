import {
  collection,
  doc,
  getDoc,
  getDocs,
  orderBy,
  query,
  where,
} from "firebase/firestore";
import { appConfig } from "@/lib/config";
import { backendContractUnavailable } from "@/lib/errors";
import { db } from "@/lib/firebase";
import { createId } from "@/lib/id";
import {
  decodeArtifact,
  decodeArtifactList,
  decodeHandoff,
  decodeHandoffList,
  decodeRun,
  decodeRunList,
  serializeStartRunCommand,
} from "@/lib/resource-contracts";
import type { AgentRun, Artifact, Handoff } from "@/types/models";
import {
  getLocalArtifacts,
  getLocalHandoffs,
  getLocalRuns,
  saveLocalArtifacts,
  saveLocalHandoffs,
  saveLocalRuns,
} from "./adapters/local-store";
import type {
  ArtifactRepository,
  HandoffRepository,
  RunRepository,
} from "./repository-contracts";

function localRuns(uid: string): AgentRun[] {
  return decodeRunList(getLocalRuns(uid));
}

function localArtifacts(uid: string): Artifact[] {
  return decodeArtifactList(getLocalArtifacts(uid));
}

function localHandoffs(uid: string): Handoff[] {
  return decodeHandoffList(getLocalHandoffs(uid));
}

function replaceRun(uid: string, value: unknown): AgentRun {
  const run = decodeRun(value);
  saveLocalRuns(
    uid,
    localRuns(uid).map((item) => (item.id === run.id ? run : item)),
  );
  return run;
}

function simulateLocalRun(uid: string, runId: string): void {
  window.setTimeout(() => {
    const run = localRuns(uid).find((item) => item.id === runId);
    if (!run || run.status !== "queued") return;
    replaceRun(uid, {
      ...run,
      status: "running",
      progress: "Working through the assignment",
      startedAt: new Date().toISOString(),
    });
  }, 500);

  window.setTimeout(() => {
    const run = localRuns(uid).find((item) => item.id === runId);
    if (!run || run.status !== "running") return;
    const timestamp = new Date().toISOString();
    const artifact = decodeArtifact({
      id: createId("artifact"),
      agentId: run.agentId,
      runId: run.id,
      type: "report",
      title: run.assignment.slice(0, 72),
      content:
        "This local preview confirms the complete run and output flow. The connected agent runtime will provide the real result.",
      sharedWithAgentIds: [],
      createdAt: timestamp,
    });
    saveLocalArtifacts(uid, [artifact, ...localArtifacts(uid)]);
    replaceRun(uid, {
      ...run,
      status: "completed",
      progress: "Assignment completed",
      artifactIds: [artifact.id],
      finishedAt: timestamp,
    });
  }, 2600);
}

const localRunRepository: RunRepository = {
  async getRuns(uid, agentId) {
    const runs = localRuns(uid);
    return agentId ? runs.filter((run) => run.agentId === agentId) : runs;
  },

  async getRun(uid, runId) {
    const run = localRuns(uid).find((item) => item.id === runId);
    if (!run) throw new Error("The selected run could not be found.");
    return run;
  },

  async startRun(uid, agentId, assignment) {
    const command = serializeStartRunCommand(assignment);
    const run = decodeRun({
      id: createId("run"),
      agentId,
      assignment: command.assignment,
      status: "queued",
      progress: "Waiting for an available runtime",
      artifactIds: [],
      createdAt: new Date().toISOString(),
    });
    saveLocalRuns(uid, [run, ...localRuns(uid)]);
    simulateLocalRun(uid, run.id);
    return run;
  },

  async cancelRun(uid, runId) {
    const run = await this.getRun(uid, runId);
    if (
      run.status !== "queued" &&
      run.status !== "running" &&
      run.status !== "waiting-for-user"
    ) {
      return run;
    }
    return replaceRun(uid, {
      ...run,
      status: "cancelled",
      progress: "Cancelled by the user",
      finishedAt: new Date().toISOString(),
    });
  },
};

const firebaseRunRepository: RunRepository = {
  async getRuns(uid, agentId) {
    const runsCollection = collection(db, "users", uid, "runs");
    const snapshot = await getDocs(
      agentId
        ? query(
            runsCollection,
            where("agentId", "==", agentId),
            orderBy("createdAt", "desc"),
          )
        : query(runsCollection, orderBy("createdAt", "desc")),
    );
    return snapshot.docs.map((item) => decodeRun(item.data(), item.id));
  },

  async getRun(uid, runId) {
    const snapshot = await getDoc(doc(db, "users", uid, "runs", runId));
    if (!snapshot.exists()) {
      throw new Error("The selected run could not be found.");
    }
    return decodeRun(snapshot.data(), snapshot.id);
  },

  async startRun() {
    throw backendContractUnavailable(
      "Agent runs",
      "POST /api/v1/agents/{agentId}/runs with an agent-attributed run response",
    );
  },

  async cancelRun() {
    throw backendContractUnavailable(
      "Run cancellation",
      "POST /api/v1/runs/{runId}/cancel with an updated run response",
    );
  },
};

const localArtifactRepository: ArtifactRepository = {
  async getArtifacts(uid, runId) {
    const artifacts = localArtifacts(uid);
    return runId
      ? artifacts.filter((artifact) => artifact.runId === runId)
      : artifacts;
  },

  async getArtifact(uid, artifactId) {
    const artifact = localArtifacts(uid).find((item) => item.id === artifactId);
    if (!artifact) throw new Error("The selected output could not be found.");
    return artifact;
  },
};

const firebaseArtifactRepository: ArtifactRepository = {
  async getArtifacts(uid, runId) {
    const artifactsCollection = collection(db, "users", uid, "artifacts");
    const snapshot = await getDocs(
      runId
        ? query(
            artifactsCollection,
            where("runId", "==", runId),
            orderBy("createdAt", "desc"),
          )
        : query(artifactsCollection, orderBy("createdAt", "desc")),
    );
    return snapshot.docs.map((item) => decodeArtifact(item.data(), item.id));
  },

  async getArtifact(uid, artifactId) {
    const snapshot = await getDoc(
      doc(db, "users", uid, "artifacts", artifactId),
    );
    if (!snapshot.exists()) {
      throw new Error("The selected output could not be found.");
    }
    return decodeArtifact(snapshot.data(), snapshot.id);
  },
};

const localHandoffRepository: HandoffRepository = {
  async getHandoffs(uid, sourceRunId) {
    const handoffs = localHandoffs(uid);
    return sourceRunId
      ? handoffs.filter((handoff) => handoff.sourceRunId === sourceRunId)
      : handoffs;
  },

  async updateHandoff(uid, handoffId, action) {
    const handoffs = localHandoffs(uid);
    const current = handoffs.find((item) => item.id === handoffId);
    if (!current) throw new Error("The handoff request could not be found.");
    const next = decodeHandoff({
      ...current,
      status: action === "approve" ? "approved" : "rejected",
    });
    saveLocalHandoffs(
      uid,
      handoffs.map((item) => (item.id === handoffId ? next : item)),
    );
    return next;
  },
};

const firebaseHandoffRepository: HandoffRepository = {
  async getHandoffs(uid, sourceRunId) {
    const handoffsCollection = collection(db, "users", uid, "handoffs");
    const snapshot = await getDocs(
      sourceRunId
        ? query(
            handoffsCollection,
            where("sourceRunId", "==", sourceRunId),
            orderBy("createdAt", "desc"),
          )
        : query(handoffsCollection, orderBy("createdAt", "desc")),
    );
    return snapshot.docs.map((item) => decodeHandoff(item.data(), item.id));
  },

  async updateHandoff() {
    throw backendContractUnavailable(
      "Handoff decisions",
      "authenticated approve/reject endpoints keyed by handoffId",
    );
  },
};

const runRepository =
  appConfig.dataMode === "local" ? localRunRepository : firebaseRunRepository;
const artifactRepository =
  appConfig.dataMode === "local"
    ? localArtifactRepository
    : firebaseArtifactRepository;
const handoffRepository =
  appConfig.dataMode === "local"
    ? localHandoffRepository
    : firebaseHandoffRepository;

export const runsService = {
  getRuns: runRepository.getRuns.bind(runRepository),
  getRun: runRepository.getRun.bind(runRepository),
  startRun: runRepository.startRun.bind(runRepository),
  cancelRun: runRepository.cancelRun.bind(runRepository),
  getArtifacts: artifactRepository.getArtifacts.bind(artifactRepository),
  getArtifact: artifactRepository.getArtifact.bind(artifactRepository),
  getHandoffs: handoffRepository.getHandoffs.bind(handoffRepository),
  updateHandoff: handoffRepository.updateHandoff.bind(handoffRepository),
} satisfies RunRepository & ArtifactRepository & HandoffRepository;
