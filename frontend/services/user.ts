import { doc, getDoc } from "firebase/firestore";
import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { db } from "@/lib/firebase";
import {
  decodeUserProfile,
  serializeCreateProfileCommand,
  serializeUpdateProfileCommand,
} from "@/lib/resource-contracts";
import type { OnboardingInput, UserProfile } from "@/types/models";
import type { ProfileRepository } from "./repository-contracts";
import { getLocalProfile, saveLocalProfile } from "./adapters/local-store";

const localProfileRepository: ProfileRepository = {
  async getProfile(uid) {
    const stored = getLocalProfile(uid);
    return stored === null ? null : decodeUserProfile(stored, uid);
  },

  async createProfile(uid, input, identity) {
    const command = serializeCreateProfileCommand(input, identity);
    const profile = decodeUserProfile(
      {
        uid,
        ...command,
        onboardingCompleted: true,
        skills: {},
      },
      uid,
    );
    saveLocalProfile(profile);
    return profile;
  },

  async updateProfile(uid, input) {
    const current = await this.getProfile(uid);
    const command = serializeUpdateProfileCommand(input);
    const profile = decodeUserProfile(
      {
        uid,
        ...command,
        onboardingCompleted: true,
        skills: current?.skills ?? {},
        displayName: current?.displayName,
        email: current?.email,
      },
      uid,
    );
    saveLocalProfile(profile);
    return profile;
  },
};

const firebaseProfileRepository: ProfileRepository = {
  async getProfile(uid) {
    const profileSnapshot = await getDoc(doc(db, "users", uid));
    return profileSnapshot.exists()
      ? decodeUserProfile(profileSnapshot.data(), uid)
      : null;
  },

  async createProfile(uid, input, identity) {
    const response = await fetchApi("/me", {
      method: "POST",
      body: JSON.stringify(serializeCreateProfileCommand(input, identity)),
    });
    return decodeUserProfile(response, uid);
  },

  async updateProfile(uid, input) {
    const response = await fetchApi("/me", {
      method: "PATCH",
      body: JSON.stringify(serializeUpdateProfileCommand(input)),
    });
    return decodeUserProfile(response, uid);
  },
};

const profileRepository =
  appConfig.dataMode === "local"
    ? localProfileRepository
    : firebaseProfileRepository;

export const userService = {
  getProfile(uid: string): Promise<UserProfile | null> {
    return profileRepository.getProfile(uid);
  },

  async getOnboardingStatus(uid: string): Promise<boolean> {
    const profile = await profileRepository.getProfile(uid);
    return profile?.onboardingCompleted === true;
  },

  submitOnboarding(
    uid: string,
    input: OnboardingInput,
    identity: { displayName?: string | null; email?: string | null },
  ): Promise<UserProfile> {
    return profileRepository.createProfile(uid, input, identity);
  },

  updateProfile(
    uid: string,
    input: OnboardingInput,
  ): Promise<UserProfile> {
    return profileRepository.updateProfile(uid, input);
  },
};
