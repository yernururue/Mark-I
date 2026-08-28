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
  DashboardSnapshot,
  Decision,
  DecisionAction,
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
  if (
    value &&
    typeof value === "object" &&
    "toDate" in value &&
    typeof value.toDate === "function"
  ) {
    return value.toDate().toISOString();
  }
  return new Date().toISOString();
}

function toIntensity(value: unknown): Intensity {
  return value === "chill" || value === "brutal" ? value : "normal";
}

function toLanguage(value: unknown): PreferredLanguage {
  return value === "ru" || value === "kk" ? value : "en";
}

function toSource(value: unknown): ObservationSource {
  return value === "github" || value === "chat" || value === "opportunity"
    ? value
    : "system";
}

function toSentiment(value: unknown): Sentiment {
  return value === "positive" || value === "negative" ? value : "neutral";
}

function toAction(value: unknown): DecisionAction {
  return value === "notify" ? "notify" : "silent";
}

function toProfile(uid: string, data: DocumentData): UserProfile {
  return {
    uid,
    displayName:
      typeof data.displayName === "string" ? data.displayName : undefined,
    email: typeof data.email === "string" ? data.email : undefined,
    goal: typeof data.goal === "string" ? data.goal : "",
    intensity: toIntensity(data.intensity),
    language: toLanguage(data.language),
    onboardingCompleted:
      data.onboardingCompleted === true || Boolean(String(data.goal ?? "").trim()),
    skills:
      data.skills && typeof data.skills === "object"
        ? (data.skills as Record<string, number>)
        : {},
  };
}

function toObservation(id: string, data: DocumentData): Observation {
  return {
    id,
    source: toSource(data.source),
    summary: typeof data.summary === "string" ? data.summary : "Activity recorded",
    concept: typeof data.concept === "string" ? data.concept : "General",
    sentiment: toSentiment(data.sentiment),
    significanceScore:
      typeof data.significance_score === "number" ? data.significance_score : 0,
    createdAt: toDateString(data.timestamp ?? data.createdAt),
  };
}

function toDecision(id: string, data: DocumentData): Decision {
  return {
    id,
    trigger: typeof data.trigger === "string" ? data.trigger : "Activity",
    significanceScore:
      typeof data.significance_score === "number" ? data.significance_score : 0,
    threshold: typeof data.threshold === "number" ? data.threshold : 0,
    action: toAction(data.action_taken ?? data.action),
    reason:
      typeof data.reason === "string" ? data.reason : "No reason was provided.",
    createdAt: toDateString(data.timestamp ?? data.createdAt),
  };
}

export function subscribeDashboard(
  uid: string,
  onData: (snapshot: DashboardSnapshot) => void,
  onError: (error: Error) => void,
): Unsubscribe {
  if (appConfig.dataMode === "local") {
    return subscribeToLocalDashboard(uid, onData);
  }

  let profile: UserProfile | null = null;
  let observations: Observation[] = [];
  let decisions: Decision[] = [];
  const ready = new Set<string>();

  const emitWhenReady = () => {
    if (ready.size === 3) {
      onData({ profile, observations, decisions });
    }
  };

  const unsubscribers = [
    onSnapshot(
      doc(db, "users", uid),
      (snapshot) => {
        profile = snapshot.exists() ? toProfile(uid, snapshot.data()) : null;
        ready.add("profile");
        emitWhenReady();
      },
      onError,
    ),
    onSnapshot(
      query(
        collection(db, "users", uid, "observations"),
        orderBy("timestamp", "desc"),
        limit(20),
      ),
      (snapshot) => {
        observations = snapshot.docs.map((item) =>
          toObservation(item.id, item.data()),
        );
        ready.add("observations");
        emitWhenReady();
      },
      onError,
    ),
    onSnapshot(
      query(
        collection(db, "users", uid, "decisions"),
        orderBy("timestamp", "desc"),
        limit(10),
      ),
      (snapshot) => {
        decisions = snapshot.docs.map((item) =>
          toDecision(item.id, item.data()),
        );
        ready.add("decisions");
        emitWhenReady();
      },
      onError,
    ),
  ];

  return () => unsubscribers.forEach((unsubscribe) => unsubscribe());
}
