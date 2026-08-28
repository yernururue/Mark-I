export type Intensity = "chill" | "normal" | "brutal";
export type PreferredLanguage = "en" | "ru" | "kk";

export interface UserProfile {
  uid: string;
  displayName?: string;
  email?: string;
  goal: string;
  intensity: Intensity;
  language: PreferredLanguage;
  onboardingCompleted: boolean;
  skills: Record<string, number>;
}

export interface OnboardingInput {
  goal: string;
  intensity: Intensity;
  language: PreferredLanguage;
}

export interface Agent {
  id: string;
  name: string;
  role: string;
  template: "mentor" | "designer" | "custom";
  objective: string;
  instructions: string;
  tone: "chill" | "normal" | "brutal" | "concise";
  toolGrants: string[];
  contextGrants: string[];
  status: "active" | "paused" | "archived";
  createdAt: string;
  updatedAt: string;
}

export type CreateAgentInput = Omit<Agent, "id" | "status" | "createdAt" | "updatedAt">;

export type RunStatus =
  | "queued"
  | "running"
  | "waiting-for-user"
  | "completed"
  | "failed"
  | "cancelled";

export interface AgentRun {
  id: string;
  agentId: string;
  assignment: string;
  status: RunStatus;
  progress?: string;
  artifactIds: string[];
  parentRunId?: string;
  error?: string;
  createdAt: string;
  startedAt?: string;
  finishedAt?: string;
}

export interface Artifact {
  id: string;
  agentId: string;
  runId: string;
  type: "report" | "design" | "plan" | "code-reference";
  title: string;
  content: string;
  sharedWithAgentIds: string[];
  createdAt: string;
}

export interface Handoff {
  id: string;
  fromAgentId: string;
  toAgentId: string;
  sourceRunId: string;
  targetRunId?: string;
  purpose: string;
  artifactIds: string[];
  status: "proposed" | "approved" | "rejected" | "completed";
  createdAt: string;
}

export type ObservationSource = "github" | "chat" | "opportunity" | "system";
export type Sentiment = "positive" | "neutral" | "negative";

export interface Observation {
  id: string;
  agentId: string;
  runId?: string;
  source: ObservationSource;
  summary: string;
  concept: string;
  sentiment: Sentiment;
  significanceScore: number;
  createdAt: string;
}

export type DecisionAction = "notify" | "silent";

export interface Decision {
  id: string;
  agentId: string;
  runId?: string;
  trigger: string;
  significanceScore: number;
  threshold: number;
  action: DecisionAction;
  reason: string;
  createdAt: string;
}

export interface DashboardSnapshot {
  profile: UserProfile | null;
  agents: Agent[];
  runs: AgentRun[];
  artifacts: Artifact[];
  handoffs: Handoff[];
  observations: Observation[];
  decisions: Decision[];
}

export interface Conversation {
  id: string;
  agentIds: string[];
  title: string;
  updatedAt: string;
}

export type MessageRole = "user" | "agent";
export type MessageStatus = "sent" | "sending" | "failed";

export interface Message {
  id: string;
  conversationId: string;
  agentId?: string;
  runId?: string;
  role: MessageRole;
  content: string;
  createdAt: string;
  status: MessageStatus;
  error?: string;
}

export interface SendMessageInput {
  agentIds: string[];
  conversationId: string;
  message: string;
  clientMessageId: string;
}

export type IntegrationStatus = "connected" | "disconnected" | "pending";

export interface IntegrationState {
  github: {
    status: IntegrationStatus;
    accountName?: string;
    repositoryCount: number;
  };
  telegram: {
    status: IntegrationStatus;
    accountName?: string;
  };
}

export interface TelegramLinkCode {
  code: string;
  expiresAt: string;
}
