import { FirebaseError } from "firebase/app";
import {
  createUserWithEmailAndPassword,
  sendPasswordResetEmail,
  signInWithEmailAndPassword,
  signInWithPopup,
  type User,
} from "firebase/auth";
import { AppError } from "@/lib/errors";
import { auth, githubProvider, googleProvider } from "@/lib/firebase";

export type AuthProviderName = "google" | "github";

function normalizeAuthError(error: unknown): AppError {
  if (!(error instanceof FirebaseError)) {
    return new AppError("Authentication failed. Please try again.", "auth");
  }

  const messages: Record<string, string> = {
    "auth/email-already-in-use": "An account already exists for this email.",
    "auth/invalid-credential": "The email or password is incorrect.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/popup-closed-by-user": "The sign-in window was closed before completion.",
    "auth/popup-blocked": "Your browser blocked the sign-in window. Allow popups and try again.",
    "auth/too-many-requests": "Too many attempts. Wait a moment and try again.",
    "auth/weak-password": "Use a password with at least six characters.",
  };

  return new AppError(
    messages[error.code] ?? "Authentication failed. Please try again.",
    error.code,
  );
}

async function withAuthErrors(action: () => Promise<User>): Promise<User> {
  try {
    return await action();
  } catch (error) {
    throw normalizeAuthError(error);
  }
}

export const authService = {
  signInWithEmail(email: string, password: string): Promise<User> {
    return withAuthErrors(async () => {
      const credential = await signInWithEmailAndPassword(auth, email, password);
      return credential.user;
    });
  },

  signUpWithEmail(email: string, password: string): Promise<User> {
    return withAuthErrors(async () => {
      const credential = await createUserWithEmailAndPassword(auth, email, password);
      return credential.user;
    });
  },

  signInWithProvider(providerName: AuthProviderName): Promise<User> {
    return withAuthErrors(async () => {
      const provider = providerName === "google" ? googleProvider : githubProvider;
      const credential = await signInWithPopup(auth, provider);
      return credential.user;
    });
  },

  async sendPasswordReset(email: string): Promise<void> {
    try {
      await sendPasswordResetEmail(auth, email);
    } catch (error) {
      throw normalizeAuthError(error);
    }
  },
};
