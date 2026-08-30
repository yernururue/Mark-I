import {
  asRecord,
  decodeList,
  enumValue,
  optionalEnumValue,
  optionalString,
  optionalTimestamp,
  recordOfNumbers,
  requiredBoolean,
  requiredNumber,
  requiredString,
  stringArray,
  timestamp,
} from "./contract-utils";
import { AppError } from "./errors";
import type {
  AgentRun,
  Artifact,
  Conversation,
  Handoff,
  IntegrationState,
  Message,
  MessageStatus,
  OnboardingInput,
  RunStatus,
  SendMessageInput,
  TelegramLinkCode,
  UserProfile,
} from "@/types/models";

export interface GithubRepositoryDto {
  fullName: string;
  private: boolean;
  connected: boolean;
}

export interface GithubCallbackDto {
  githubUsername: string;
  repos: GithubRepositoryDto[];
}

export function decodeUserProfile(
  value: unknown,
  expectedUid?: string,
): UserProfile {
  const data = asRecord(value, "profile");
  const uid = requiredString(data.uid ?? expectedUid, "profile uid");

  if (expectedUid && uid !== expectedUid) {
    throw new AppError(
      "The profile identifier does not match the signed-in user.",
      "invalid-response",
    );
  }

  return {
    uid,
    displayName: optionalString(data.displayName, "profile displayName"),
    email: optionalString(data.email, "profile email"),
    goal: requiredString(data.goal, "profile goal"),
    intensity: enumValue(
      data.intensity,
      ["chill", "normal", "brutal"],
      "profile intensity",
    ),
    language: enumValue(data.language, ["en", "ru", "kk"], "profile language"),
    onboardingCompleted: requiredBoolean(
      data.onboardingCompleted,
      "profile onboardingCompleted",
    ),
    skills: recordOfNumbers(data.skills, "profile skills", { min: 0, max: 10 }),
  };
}

function normalizeOnboardingInput(input: OnboardingInput): OnboardingInput {
  const goal = input.goal.trim();
  if (!goal) {
    throw new AppError("A workspace goal is required.", "invalid-input");
  }

  return {
    goal,
    intensity: enumValue(
      input.intensity,
      ["chill", "normal", "brutal"],
      "profile intensity",
    ),
    language: enumValue(
      input.language,
      ["en", "ru", "kk"],
      "profile language",
    ),
  };
}

export function serializeCreateProfileCommand(
  input: OnboardingInput,
  identity: { displayName?: string | null; email?: string | null },
): Record<string, unknown> {
  const normalized = normalizeOnboardingInput(input);
  return {
    displayName:
      identity.displayName?.trim() || identity.email?.trim() || "Mark-I user",
    ...normalized,
  };
}

export function serializeUpdateProfileCommand(
  input: OnboardingInput,
): Record<string, unknown> {
  return { ...normalizeOnboardingInput(input) };
}

export function decodeConversation(value: unknown): Conversation {
  const data = asRecord(value, "conversation");
  return {
    id: requiredString(
      data.conversationId ?? data.id,
      "conversation id",
    ),
    agentId: requiredString(data.agentId, "conversation agentId"),
    title: requiredString(data.title, "conversation title"),
    updatedAt: timestamp(data.updatedAt, "conversation updatedAt"),
  };
}

export function decodeConversationList(value: unknown): Conversation[] {
  return decodeList(value, "conversations", decodeConversation);
}

export function decodeMessage(value: unknown): Message {
  const data = asRecord(value, "message");
  return {
    id: requiredString(data.messageId ?? data.id, "message id"),
    conversationId: requiredString(
      data.conversationId,
      "message conversationId",
    ),
    agentId: requiredString(data.agentId, "message agentId"),
    runId: optionalString(data.runId, "message runId"),
    role: enumValue(data.role, ["user", "agent"], "message role"),
    content: requiredString(data.content ?? data.text, "message content"),
    createdAt: timestamp(data.createdAt, "message createdAt"),
    status:
      optionalEnumValue<MessageStatus>(
        data.status,
        ["sent", "sending", "failed"],
        "message status",
      ) ?? "sent",
    error: optionalString(data.error, "message error"),
  };
}

export function decodeMessageList(value: unknown): Message[] {
  return decodeList(value, "messages", decodeMessage);
}

export function serializeSendMessageCommand(
  input: SendMessageInput,
): Record<string, unknown> {
  const message = input.message.trim();
  if (!message) throw new AppError("A message is required.", "invalid-input");

  return {
    agentId: requiredString(input.agentId, "message agentId"),
    conversationId: requiredString(
      input.conversationId,
      "message conversationId",
    ),
    text: message,
    clientMessageId: requiredString(
      input.clientMessageId,
      "message clientMessageId",
    ),
  };
}

export function decodeRun(value: unknown, documentId?: string): AgentRun {
  const data = asRecord(value, "run");
  const id = requiredString(data.runId ?? data.id ?? documentId, "run id");
  if (documentId && id !== documentId) {
    throw new AppError(
      "The run identifier does not match its Firestore document.",
      "invalid-response",
    );
  }
  return {
    id,
    agentId: requiredString(data.agentId, "run agentId"),
    assignment: requiredString(data.assignment, "run assignment"),
    status: enumValue<RunStatus>(
      data.status,
      [
        "queued",
        "running",
        "waiting-for-user",
        "completed",
        "failed",
        "cancelled",
      ],
      "run status",
    ),
    progress: optionalString(data.progress, "run progress"),
    artifactIds: stringArray(data.artifactIds, "run artifactIds"),
    parentRunId: optionalString(data.parentRunId, "run parentRunId"),
    error: optionalString(data.error, "run error"),
    createdAt: timestamp(data.createdAt, "run createdAt"),
    startedAt: optionalTimestamp(data.startedAt, "run startedAt"),
    finishedAt: optionalTimestamp(data.finishedAt, "run finishedAt"),
  };
}

export function decodeRunList(value: unknown): AgentRun[] {
  return decodeList(value, "runs", decodeRun);
}

export function serializeStartRunCommand(
  assignment: string,
): Record<string, unknown> {
  const normalized = assignment.trim();
  if (!normalized) {
    throw new AppError("A run assignment is required.", "invalid-input");
  }

  return { assignment: normalized, inputArtifactIds: [] };
}

export function decodeArtifact(value: unknown, documentId?: string): Artifact {
  const data = asRecord(value, "artifact");
  const id = requiredString(
    data.artifactId ?? data.id ?? documentId,
    "artifact id",
  );
  if (documentId && id !== documentId) {
    throw new AppError(
      "The artifact identifier does not match its Firestore document.",
      "invalid-response",
    );
  }
  return {
    id,
    agentId: requiredString(data.agentId, "artifact agentId"),
    runId: requiredString(data.runId, "artifact runId"),
    type: enumValue(
      data.type,
      ["report", "design", "plan", "code-reference"],
      "artifact type",
    ),
    title: requiredString(data.title, "artifact title"),
    content: requiredString(data.content, "artifact content"),
    sharedWithAgentIds: stringArray(
      data.sharedWithAgentIds,
      "artifact sharedWithAgentIds",
    ),
    createdAt: timestamp(data.createdAt, "artifact createdAt"),
  };
}

export function decodeArtifactList(value: unknown): Artifact[] {
  return decodeList(value, "artifacts", decodeArtifact);
}

export function decodeHandoff(value: unknown, documentId?: string): Handoff {
  const data = asRecord(value, "handoff");
  const id = requiredString(
    data.handoffId ?? data.id ?? documentId,
    "handoff id",
  );
  if (documentId && id !== documentId) {
    throw new AppError(
      "The handoff identifier does not match its Firestore document.",
      "invalid-response",
    );
  }
  return {
    id,
    fromAgentId: requiredString(data.fromAgentId, "handoff fromAgentId"),
    toAgentId: requiredString(data.toAgentId, "handoff toAgentId"),
    sourceRunId: requiredString(data.sourceRunId, "handoff sourceRunId"),
    targetRunId: optionalString(data.targetRunId, "handoff targetRunId"),
    purpose: requiredString(data.purpose, "handoff purpose"),
    artifactIds: stringArray(data.artifactIds, "handoff artifactIds"),
    status: enumValue(
      data.status,
      ["proposed", "approved", "rejected", "completed"],
      "handoff status",
    ),
    createdAt: timestamp(data.createdAt, "handoff createdAt"),
  };
}

export function decodeHandoffList(value: unknown): Handoff[] {
  return decodeList(value, "handoffs", decodeHandoff);
}

function decodeGithubRepository(value: unknown): GithubRepositoryDto {
  const data = asRecord(value, "GitHub repository");
  return {
    fullName: requiredString(data.fullName, "GitHub repository fullName"),
    private: requiredBoolean(data.private, "GitHub repository private"),
    connected:
      data.connected === undefined
        ? false
        : requiredBoolean(data.connected, "GitHub repository connected"),
  };
}

export function decodeGithubRepositories(value: unknown): GithubRepositoryDto[] {
  const data = asRecord(value, "GitHub repositories");
  return decodeList(data.repos, "GitHub repositories", decodeGithubRepository);
}

export function decodeIntegrationProfile(
  value: unknown,
  connectedRepositoryCount: number,
): IntegrationState {
  const data = asRecord(value, "integration profile");
  const githubConnected = requiredBoolean(
    data.githubConnected,
    "integration githubConnected",
  );
  const telegramLinked = requiredBoolean(
    data.telegramLinked,
    "integration telegramLinked",
  );

  return {
    github: {
      status: githubConnected ? "connected" : "disconnected",
      accountName: optionalString(
        data.githubUsername,
        "integration githubUsername",
      ),
      repositoryCount: requiredNumber(
        connectedRepositoryCount,
        "integration repositoryCount",
        { min: 0, integer: true },
      ),
    },
    telegram: {
      status: telegramLinked ? "connected" : "disconnected",
      accountName: optionalString(
        data.telegramUsername,
        "integration telegramUsername",
      ),
    },
  };
}

export function decodeIntegrationState(value: unknown): IntegrationState {
  const data = asRecord(value, "integrations");
  const github = asRecord(data.github, "GitHub integration");
  const telegram = asRecord(data.telegram, "Telegram integration");
  return {
    github: {
      status: enumValue(
        github.status,
        ["connected", "disconnected", "pending"],
        "GitHub integration status",
      ),
      accountName: optionalString(
        github.accountName,
        "GitHub integration accountName",
      ),
      repositoryCount: requiredNumber(
        github.repositoryCount,
        "GitHub integration repositoryCount",
        { min: 0, integer: true },
      ),
    },
    telegram: {
      status: enumValue(
        telegram.status,
        ["connected", "disconnected", "pending"],
        "Telegram integration status",
      ),
      accountName: optionalString(
        telegram.accountName,
        "Telegram integration accountName",
      ),
    },
  };
}

export function decodeGithubAuthUrl(value: unknown): string {
  const data = asRecord(value, "GitHub auth URL");
  const authUrl = requiredString(data.authUrl, "GitHub authUrl");
  try {
    const parsed = new URL(authUrl);
    if (parsed.protocol !== "https:") throw new Error("not HTTPS");
  } catch {
    throw new AppError(
      "The GitHub authUrl field is invalid.",
      "invalid-response",
    );
  }
  return authUrl;
}

export function decodeGithubCallback(value: unknown): GithubCallbackDto {
  const data = asRecord(value, "GitHub callback");
  return {
    githubUsername: requiredString(
      data.githubUsername,
      "GitHub callback githubUsername",
    ),
    repos: decodeList(data.repos, "GitHub callback repositories", decodeGithubRepository),
  };
}

export function serializeGithubCallbackCommand(
  code: string,
  state: string,
): Record<string, unknown> {
  return {
    code: requiredString(code, "GitHub callback code"),
    state: requiredString(state, "GitHub callback state"),
  };
}

export function decodeTelegramLinkCode(value: unknown): TelegramLinkCode {
  const data = asRecord(value, "Telegram link code");
  const code = requiredString(data.code, "Telegram link code");
  if (!/^[A-Z0-9]{6}$/.test(code)) {
    throw new AppError(
      "The Telegram link code field is invalid.",
      "invalid-response",
    );
  }
  return {
    code,
    expiresAt: timestamp(data.expiresAt, "Telegram link expiresAt"),
  };
}

export function decodeSuccess(value: unknown, label: string): void {
  const data = asRecord(value, label);
  if (!requiredBoolean(data.success ?? data.disconnected, `${label} success`)) {
    throw new AppError(`${label} did not complete.`, "invalid-response");
  }
}
