"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { getErrorMessage } from "@/lib/errors";
import { authService, type AuthProviderName } from "@/services/auth";
import { userService } from "@/services/user";

type AuthMode = "login" | "signup";

interface AuthFormProps {
  initialMode?: AuthMode;
  nextPath?: string;
}

function safeNextPath(value?: string): string | null {
  if (!value || !value.startsWith("/") || value.startsWith("//")) return null;
  if (value === "/login" || value === "/onboarding") return null;
  return value;
}

export default function AuthForm({
  initialMode = "login",
  nextPath,
}: AuthFormProps) {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>(initialMode);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const finishAuthentication = async (uid: string) => {
    const onboardingComplete = await userService.getOnboardingStatus(uid);
    const requestedPath = safeNextPath(nextPath);
    router.replace(
      onboardingComplete ? (requestedPath ?? "/dashboard") : "/onboarding",
    );
  };

  const handleEmailSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;

    if (mode === "signup" && password !== repeatPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 6) {
      setError("Use a password with at least six characters.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const user =
        mode === "signup"
          ? await authService.signUpWithEmail(email.trim(), password)
          : await authService.signInWithEmail(email.trim(), password);
      await finishAuthentication(user.uid);
    } catch (authError) {
      setError(getErrorMessage(authError, "Authentication failed. Please try again."));
      setSubmitting(false);
    }
  };

  const handleProvider = async (provider: AuthProviderName) => {
    if (submitting) return;
    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      const user = await authService.signInWithProvider(provider);
      await finishAuthentication(user.uid);
    } catch (authError) {
      setError(getErrorMessage(authError, "Authentication failed. Please try again."));
      setSubmitting(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!email.trim()) {
      setError("Enter your email first, then request a reset link.");
      return;
    }

    setSubmitting(true);
    setError(null);
    setNotice(null);

    try {
      await authService.sendPasswordReset(email.trim());
      setNotice("Password reset instructions were sent to your email.");
    } catch (resetError) {
      setError(getErrorMessage(resetError, "The reset email could not be sent."));
    } finally {
      setSubmitting(false);
    }
  };

  const changeMode = () => {
    setMode((current) => (current === "login" ? "signup" : "login"));
    setPassword("");
    setRepeatPassword("");
    setError(null);
    setNotice(null);
  };

  return (
    <section className="auth-card" aria-labelledby="auth-title">
      <div className="auth-card__heading">
        <h1 id="auth-title">{mode === "signup" ? "Create your account" : "Welcome back"}</h1>
        <p>
          {mode === "signup"
            ? "Set up your workspace and first agent in a few minutes."
            : "Continue to your agents, runs, outputs, and conversations."}
        </p>
      </div>

      <div className="auth-providers">
        <button
          type="button"
          className="button button--secondary"
          disabled={submitting}
          onClick={() => handleProvider("google")}
        >
          Continue with Google
        </button>
        <button
          type="button"
          className="button button--secondary"
          disabled={submitting}
          onClick={() => handleProvider("github")}
        >
          Continue with GitHub
        </button>
      </div>

      <div className="auth-divider"><span>or use email</span></div>

      <form className="form-stack" onSubmit={handleEmailSubmit} noValidate>
        <label className="field">
          <span>Email</span>
          <input
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            required
          />
        </label>

        <label className="field">
          <span className="field__label-row">
            Password
            {mode === "login" ? (
              <button type="button" className="text-button" onClick={handlePasswordReset}>
                Forgot password?
              </button>
            ) : null}
          </span>
          <input
            type="password"
            autoComplete={mode === "signup" ? "new-password" : "current-password"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </label>

        {mode === "signup" ? (
          <label className="field">
            <span>Repeat password</span>
            <input
              type="password"
              autoComplete="new-password"
              value={repeatPassword}
              onChange={(event) => setRepeatPassword(event.target.value)}
              required
            />
          </label>
        ) : null}

        {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
        {notice ? <p className="form-message form-message--success" role="status">{notice}</p> : null}

        <button type="submit" className="button button--primary" disabled={submitting}>
          {submitting
            ? "Please wait…"
            : mode === "signup"
              ? "Create account"
              : "Log in"}
        </button>
      </form>

      <p className="auth-switch">
        {mode === "signup" ? "Already have an account?" : "New to Mark-I?"}{" "}
        <button type="button" className="text-button" onClick={changeMode}>
          {mode === "signup" ? "Log in" : "Create an account"}
        </button>
      </p>
    </section>
  );
}
