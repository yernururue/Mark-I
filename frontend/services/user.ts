import { doc, getDoc } from "firebase/firestore";
import { appConfig } from "@/lib/config";
import { fetchApi } from "@/lib/api";
import { db } from "@/lib/firebase";
import type { OnboardingInput, UserProfile } from "@/types/models";
import { getLocalProfile, saveLocalProfile } from "./adapters/local-store";

function isIntensity(value: unknown): value is UserProfile["intensity"] {
  return value === "chill" || value === "normal" || value === "brutal";
}

function isLanguage(value: unknown): value is UserProfile["language"] {
  return value === "en" || value === "ru" || value === "kk";
}

function toProfile(uid: string, data: Record<string, unknown>): UserProfile | null {
  const goal = typeof data.goal === "string" ? data.goal : "";
  const intensity = isIntensity(data.intensity) ? data.intensity : "normal";
  const language = isLanguage(data.language) ? data.language : "en";
  const onboardingCompleted =
    data.onboardingCompleted === true || Boolean(goal.trim());

  if (!onboardingCompleted) return null;

  const skills =
    data.skills && typeof data.skills === "object"
      ? (data.skills as Record<string, number>)
      : {};

  return {
    uid,
    goal,
    intensity,
    language,
    onboardingCompleted,
    skills,
    displayName:
      typeof data.displayName === "string" ? data.displayName : undefined,
    email: typeof data.email === "string" ? data.email : undefined,
  };
}

export const userService = {
  async getProfile(uid: string): Promise<UserProfile | null> {
    if (appConfig.dataMode === "local") {
      return getLocalProfile(uid);
    }

    const profileSnapshot = await getDoc(doc(db, "users", uid));
    return profileSnapshot.exists()
      ? toProfile(uid, profileSnapshot.data())
      : null;
  },

  async getOnboardingStatus(uid: string): Promise<boolean> {
    const profile = await this.getProfile(uid);
    return profile?.onboardingCompleted === true;
  },

  async submitOnboarding(
    uid: string,
    input: OnboardingInput,
    identity: { displayName?: string | null; email?: string | null },
  ): Promise<UserProfile> {
    if (appConfig.dataMode === "local") {
      const profile: UserProfile = {
        uid,
        goal: input.goal.trim(),
        intensity: input.intensity,
        language: input.language,
        onboardingCompleted: true,
        skills: {},
        displayName: identity.displayName ?? undefined,
        email: identity.email ?? undefined,
      };
      saveLocalProfile(profile);
      return profile;
    }

    return fetchApi<UserProfile>("/users/onboarding", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async updateProfile(
    uid: string,
    input: OnboardingInput,
  ): Promise<UserProfile> {
    if (appConfig.dataMode === "local") {
      const current = getLocalProfile(uid);
      const profile: UserProfile = {
        uid,
        goal: input.goal.trim(),
        intensity: input.intensity,
        language: input.language,
        onboardingCompleted: true,
        skills: current?.skills ?? {},
        displayName: current?.displayName,
        email: current?.email,
      };
      saveLocalProfile(profile);
      return profile;
    }

    return fetchApi<UserProfile>("/users/me", {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },
};
