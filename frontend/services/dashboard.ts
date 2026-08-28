import {
  collection,
  doc,
  limit,
  onSnapshot,
  orderBy,
  query,
  type DocumentData,
  type Unsubscribe,
} from "firebase/firestore";
import { appConfig } from "@/lib/config";
import { db } from "@/lib/firebase";
import type {
  Agent,
  AgentRun,
  Artifact,
  DashboardSnapshot,
  Decision,
  DecisionAction,
  Handoff,
  Intensity,
  Observation,
  ObservationSource,
  PreferredLanguage,
  Sentiment,
  UserProfile,
} from "@/types/models";
import { subscribeToLocalDashboard } from "./adapters/local-store";

function toDateString(value: unknown): string {
  if (typeof value === "string") return value;
  if (value instanceof Date) return value.toISOString();
  if (value && typeof value === "object" && "toDate" in value && typeof value.toDate === "function") {
    return value.toDate().toISOString();
  }
  return new Date().toISOString();
}

function stringArray(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function toIntensity(value: unknown): Intensity {
  return value === "chill" || value === "brutal" ? value : "normal";
}

function toLanguage(value: unknown): PreferredLanguage {
  return value === "ru" || value === "kk" ? value : "en";
}

function toSource(value: unknown): ObservationSource {
  return value === "github" || value === "chat" || value === "opportunity" ? value : "system";
}

function toSentiment(value: unknown): Sentiment {
  return value === "positive" || value === "negative" ? value : "neutral";
}

function toAction(value: unknown): DecisionAction {
  return value === "notify" || value === "notified" ? "notify" : "silent";
}

function toProfile(uid: string, data: DocumentData): UserProfile {
  return {
    uid,
    displayName: typeof data.displayName === "string" ? data.displayName : undefined,
    email: typeof data.email === "string" ? data.email : undefined,
    goal: typeof data.goal === "string" ? data.goal : "",
    intensity: toIntensity(data.intensity),
    language: toLanguage(data.language),
    onboardingCompleted: data.onboardingCompleted === true || Boolean(String(data.goal ?? "").trim()),
    skills: data.skills && typeof data.skills === "object" ? (data.skills as Record<string, number>) : {},
  };
}

function toAgent(id: string, data: DocumentData): Agent {
  const template = data.template === "mentor" || data.template === "designer" ? data.template : "custom";
  const status = data.status === "paused" || data.status === "archived" ? data.status : "active";
  const tone = data.tone === "chill" || data.tone === "brutal" || data.tone === "concise" ? data.tone : "normal";
  return {
    id,
    name: typeof data.name === "string" ? data.name : "Unnamed agent",
    role: typeof data.role === "string" ? data.role : "custom",
    template,
    objective: typeof data.objective === "string" ? data.objective : "",
    instructions: typeof data.instructions === "string" ? data.instructions : "",
    tone,
    toolGrants: stringArray(data.toolGrants),
    contextGrants: stringArray(data.contextGrants),
    status,
    createdAt: toDateString(data.createdAt),
    updatedAt: toDateString(data.updatedAt),
  };
}

function toRun(id: string, data: DocumentData): AgentRun {
  const statuses: AgentRun["status"][] = ["queued", "running", "waiting-for-user", "completed", "failed", "cancelled"];
  const status = statuses.includes(data.status) ? data.status : "queued";
  return {
    id,
    agentId: typeof data.agentId === "string" ? data.agentId : "unknown-agent",
    assignment: typeof data.assignment === "string" ? data.assignment : "",
    status,
    progress: typeof data.progress === "string" ? data.progress : undefined,
    artifactIds: stringArray(data.artifactIds),
    parentRunId: typeof data.parentRunId === "string" ? data.parentRunId : undefined,
    error: typeof data.error?.message === "string" ? data.error.message : undefined,
    createdAt: toDateString(data.createdAt),
    startedAt: data.startedAt ? toDateString(data.startedAt) : undefined,
    finishedAt: data.finishedAt ? toDateString(data.finishedAt) : undefined,
  };
}

function toArtifact(id: string, data: DocumentData): Artifact {
  const type = data.type === "design" || data.type === "plan" || data.type === "code-reference" ? data.type : "report";
  return {
    id,
    agentId: typeof data.agentId === "string" ? data.agentId : "unknown-agent",
    runId: typeof data.runId === "string" ? data.runId : "unknown-run",
    type,
    title: typeof data.title === "string" ? data.title : "Untitled output",
    content: typeof data.content === "string" ? data.content : JSON.stringify(data.content ?? {}),
    sharedWithAgentIds: stringArray(data.sharedWithAgentIds),
    createdAt: toDateString(data.createdAt),
  };
}

function toHandoff(id: string, data: DocumentData): Handoff {
  const status = data.status === "approved" || data.status === "rejected" || data.status === "completed" ? data.status : "proposed";
  return {
    id,
    fromAgentId: typeof data.fromAgentId === "string" ? data.fromAgentId : "unknown-agent",
    toAgentId: typeof data.toAgentId === "string" ? data.toAgentId : "unknown-agent",
    sourceRunId: typeof data.sourceRunId === "string" ? data.sourceRunId : "unknown-run",
    targetRunId: typeof data.targetRunId === "string" ? data.targetRunId : undefined,
    purpose: typeof data.purpose === "string" ? data.purpose : "",
    artifactIds: stringArray(data.artifactIds),
    status,
    createdAt: toDateString(data.createdAt),
  };
}

function toObservation(id: string, data: DocumentData): Observation {
  return {
    id,
    agentId: typeof data.agentId === "string" ? data.agentId : "unknown-agent",
    runId: typeof data.runId === "string" ? data.runId : undefined,
    source: toSource(data.source),
    summary: typeof data.summary === "string" ? data.summary : "Activity recorded",
    concept: typeof data.concept === "string" ? data.concept : "General",
    sentiment: toSentiment(data.sentiment),
    significanceScore: typeof data.significanceScore === "number" ? data.significanceScore : 0,
    createdAt: toDateString(data.createdAt),
  };
}

function toDecision(id: string, data: DocumentData): Decision {
  return {
    id,
    agentId: typeof data.agentId === "string" ? data.agentId : "unknown-agent",
    runId: typeof data.runId === "string" ? data.runId : undefined,
    trigger: typeof data.trigger === "string" ? data.trigger : "Activity",
    significanceScore: typeof data.significanceScore === "number" ? data.significanceScore : 0,
    threshold: typeof data.threshold === "number" ? data.threshold : 0,
    action: toAction(data.action),
    reason: typeof data.reason === "string" ? data.reason : "No reason was provided.",
    createdAt: toDateString(data.createdAt),
  };
}

export function subscribeDashboard(
  uid: string,
  onData: (snapshot: DashboardSnapshot) => void,
  onError: (error: Error) => void,
): Unsubscribe {
  if (appConfig.dataMode === "local") return subscribeToLocalDashboard(uid, onData);

  let snapshot: DashboardSnapshot = {
    profile: null, agents: [], runs: [], artifacts: [], handoffs: [], observations: [], decisions: [],
  };
  const ready = new Set<string>();
  const update = <K extends keyof DashboardSnapshot>(key: K, value: DashboardSnapshot[K]) => {
    snapshot = { ...snapshot, [key]: value };
    ready.add(key);
    if (ready.size === 7) onData(snapshot);
  };

  const subscribers = [
    onSnapshot(doc(db, "users", uid), (item) => update("profile", item.exists() ? toProfile(uid, item.data()) : null), onError),
    onSnapshot(query(collection(db, "users", uid, "agents"), orderBy("updatedAt", "desc")), (items) => update("agents", items.docs.map((item) => toAgent(item.id, item.data()))), onError),
    onSnapshot(query(collection(db, "users", uid, "runs"), orderBy("createdAt", "desc"), limit(30)), (items) => update("runs", items.docs.map((item) => toRun(item.id, item.data()))), onError),
    onSnapshot(query(collection(db, "users", uid, "artifacts"), orderBy("createdAt", "desc"), limit(20)), (items) => update("artifacts", items.docs.map((item) => toArtifact(item.id, item.data()))), onError),
    onSnapshot(query(collection(db, "users", uid, "handoffs"), orderBy("createdAt", "desc"), limit(20)), (items) => update("handoffs", items.docs.map((item) => toHandoff(item.id, item.data()))), onError),
    onSnapshot(query(collection(db, "users", uid, "observations"), orderBy("createdAt", "desc"), limit(20)), (items) => update("observations", items.docs.map((item) => toObservation(item.id, item.data()))), onError),
    onSnapshot(query(collection(db, "users", uid, "decisions"), orderBy("createdAt", "desc"), limit(10)), (items) => update("decisions", items.docs.map((item) => toDecision(item.id, item.data()))), onError),
  ];
  return () => subscribers.forEach((unsubscribe) => unsubscribe());
}
