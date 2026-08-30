import type {
  Agent,
  AgentRun,
  Artifact,
  Conversation,
  CreateAgentInput,
  Handoff,
  IntegrationState,
  Message,
  OnboardingInput,
  SendMessageInput,
  TelegramLinkCode,
  UpdateAgentInput,
  UserProfile,
} from "@/types/models";

export type RepositoryUnsubscribe = () => void;

export interface ProfileRepository {
  getProfile(uid: string): Promise<UserProfile | null>;
  createProfile(
    uid: string,
    input: OnboardingInput,
    identity: { displayName?: string | null; email?: string | null },
  ): Promise<UserProfile>;
  updateProfile(uid: string, input: OnboardingInput): Promise<UserProfile>;
}

export interface AgentRepository {
  subscribeAgents(
    uid: string,
    onData: (agents: Agent[]) => void,
    onError: (error: Error) => void,
  ): RepositoryUnsubscribe;
  getAgents(uid: string): Promise<Agent[]>;
  getAgent(uid: string, agentId: string): Promise<Agent>;
  createAgent(uid: string, input: CreateAgentInput): Promise<Agent>;
  updateAgent(
    uid: string,
    agentId: string,
    input: UpdateAgentInput,
  ): Promise<Agent>;
}

export interface ConversationRepository {
  getConversations(uid: string, agentId?: string): Promise<Conversation[]>;
  getOrCreateConversation(uid: string, agentId: string): Promise<Conversation>;
}

export interface MessageRepository {
  getMessages(
    uid: string,
    conversation: Conversation,
  ): Promise<Message[]>;
  sendMessage(uid: string, input: SendMessageInput): Promise<Message[]>;
}

export interface RunRepository {
  getRuns(uid: string, agentId?: string): Promise<AgentRun[]>;
  getRun(uid: string, runId: string): Promise<AgentRun>;
  startRun(
    uid: string,
    agentId: string,
    assignment: string,
  ): Promise<AgentRun>;
  cancelRun(uid: string, runId: string): Promise<AgentRun>;
}

export interface ArtifactRepository {
  getArtifacts(uid: string, runId?: string): Promise<Artifact[]>;
  getArtifact(uid: string, artifactId: string): Promise<Artifact>;
}

export interface HandoffRepository {
  getHandoffs(uid: string, sourceRunId?: string): Promise<Handoff[]>;
  updateHandoff(
    uid: string,
    handoffId: string,
    action: "approve" | "reject",
  ): Promise<Handoff>;
}

export interface IntegrationRepository {
  getState(uid: string): Promise<IntegrationState>;
  connectGithub(uid: string): Promise<IntegrationState>;
  disconnectGithub(uid: string): Promise<IntegrationState>;
  completeGithubConnection(
    uid: string,
    code: string,
    state: string,
  ): Promise<IntegrationState>;
  createTelegramLink(uid: string): Promise<TelegramLinkCode>;
  disconnectTelegram(uid: string): Promise<IntegrationState>;
}
