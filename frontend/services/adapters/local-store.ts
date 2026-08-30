import type {
  Agent,
  AgentRun,
  Artifact,
  Conversation,
  Handoff,
  IntegrationState,
  Message,
  UserProfile,
} from "@/types/models";
import { AppError } from "@/lib/errors";

const STORAGE_PREFIX = "mark-i";
const STORAGE_EVENT = "mark-i:storage";

function storageKey(uid: string, name: string): string {
  return `${STORAGE_PREFIX}:${uid}:${name}`;
}

function readValue(key: string, fallback: unknown): unknown {
  if (typeof window === "undefined") return fallback;

  const value = window.localStorage.getItem(key);
  if (!value) return fallback;

  try {
    return JSON.parse(value) as unknown;
  } catch {
    throw new AppError(
      `Local preview data at ${key} is not valid JSON.`,
      "invalid-response",
    );
  }
}

function writeValue<T>(key: string, value: T): void {
  if (typeof window === "undefined") return;

  window.localStorage.setItem(key, JSON.stringify(value));
  window.dispatchEvent(new CustomEvent(STORAGE_EVENT, { detail: key }));
}

function subscribeToLocalValue(
  uid: string,
  name: string,
  read: () => unknown,
  onChange: (value: unknown) => void,
  onError?: (error: Error) => void,
): () => void {
  const key = storageKey(uid, name);
  const notify = () => {
    try {
      onChange(read());
    } catch (error) {
      if (onError) {
        onError(error instanceof Error ? error : new Error("Local preview data is invalid."));
        return;
      }
      throw error;
    }
  };
  const handleStorage = (event: Event) => {
    if (event instanceof CustomEvent && event.detail === key) {
      notify();
    }

    if (event instanceof StorageEvent && event.key === key) {
      notify();
    }
  };

  notify();
  window.addEventListener(STORAGE_EVENT, handleStorage);
  window.addEventListener("storage", handleStorage);

  return () => {
    window.removeEventListener(STORAGE_EVENT, handleStorage);
    window.removeEventListener("storage", handleStorage);
  };
}

export function getLocalProfile(uid: string): unknown {
  return readValue(storageKey(uid, "profile"), null);
}

export function saveLocalProfile(profile: UserProfile): void {
  writeValue(storageKey(profile.uid, "profile"), profile);
}

export function getLocalAgents(uid: string): unknown {
  return readValue(storageKey(uid, "agents"), []);
}

export function saveLocalAgents(uid: string, agents: Agent[]): void {
  writeValue(storageKey(uid, "agents"), agents);
}

export function subscribeToLocalAgents(
  uid: string,
  onChange: (agents: unknown) => void,
  onError?: (error: Error) => void,
): () => void {
  return subscribeToLocalValue(
    uid,
    "agents",
    () => getLocalAgents(uid),
    onChange,
    onError,
  );
}

export function getLocalRuns(uid: string): unknown {
  return readValue(storageKey(uid, "runs"), []);
}

export function saveLocalRuns(uid: string, runs: AgentRun[]): void {
  writeValue(storageKey(uid, "runs"), runs);
}

export function getLocalArtifacts(uid: string): unknown {
  return readValue(storageKey(uid, "artifacts"), []);
}

export function saveLocalArtifacts(uid: string, artifacts: Artifact[]): void {
  writeValue(storageKey(uid, "artifacts"), artifacts);
}

export function getLocalHandoffs(uid: string): unknown {
  return readValue(storageKey(uid, "handoffs"), []);
}

export function saveLocalHandoffs(uid: string, handoffs: Handoff[]): void {
  writeValue(storageKey(uid, "handoffs"), handoffs);
}

export function getLocalConversations(uid: string): unknown {
  return readValue(storageKey(uid, "conversations"), []);
}

export function saveLocalConversations(
  uid: string,
  conversations: Conversation[],
): void {
  writeValue(storageKey(uid, "conversations"), conversations);
}

export function getLocalMessages(uid: string, conversationId: string): unknown {
  return readValue(storageKey(uid, `messages:${conversationId}`), []);
}

export function saveLocalMessages(
  uid: string,
  conversationId: string,
  messages: Message[],
): void {
  writeValue(storageKey(uid, `messages:${conversationId}`), messages);
}

const EMPTY_INTEGRATIONS: IntegrationState = {
  github: { status: "disconnected", repositoryCount: 0 },
  telegram: { status: "disconnected" },
};

export function getLocalIntegrations(uid: string): unknown {
  return readValue(storageKey(uid, "integrations"), EMPTY_INTEGRATIONS);
}

export function saveLocalIntegrations(
  uid: string,
  integrations: IntegrationState,
): void {
  writeValue(storageKey(uid, "integrations"), integrations);
}
