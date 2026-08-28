"use client";

import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import RouteGuard from "@/components/RouteGuard";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/errors";
import { userService } from "@/services/user";
import type {
  Intensity,
  OnboardingInput,
  PreferredLanguage,
} from "@/types/models";

const INTENSITIES: Array<{
  value: Intensity;
  name: string;
  description: string;
}> = [
  {
    value: "chill",
    name: "Chill",
    description: "Only contact me when something is especially useful.",
  },
  {
    value: "normal",
    name: "Normal",
    description: "Balance useful nudges with quiet observation.",
  },
  {
    value: "brutal",
    name: "Brutal",
    description: "Be direct and point out smaller gaps as they appear.",
  },
];

const LANGUAGES: Array<{ value: PreferredLanguage; name: string }> = [
  { value: "en", name: "English" },
  { value: "ru", name: "Русский" },
  { value: "kk", name: "Қазақша" },
];

function OnboardingContent() {
  const { user } = useAuth();
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState("");
  const [intensity, setIntensity] = useState<Intensity>("normal");
  const [language, setLanguage] = useState<PreferredLanguage>("en");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const nextStep = () => {
    if (step === 0 && goal.trim().length < 10) {
      setError("Describe a concrete goal in at least ten characters.");
      return;
    }
    setError(null);
    setStep((current) => Math.min(current + 1, 2));
  };

  const previousStep = () => {
    setError(null);
    setStep((current) => Math.max(current - 1, 0));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user || submitting) return;

    const input: OnboardingInput = { goal: goal.trim(), intensity, language };
    setSubmitting(true);
    setError(null);

    try {
      await userService.submitOnboarding(user.uid, input, {
        displayName: user.displayName,
        email: user.email,
      });
      router.replace("/dashboard");
    } catch (submissionError) {
      setError(
        getErrorMessage(
          submissionError,
          "Your setup could not be saved. Please try again.",
        ),
      );
      setSubmitting(false);
    }
  };

  return (
    <main className="onboarding-page">
      <div className="onboarding-frame">
        <header className="onboarding-header">
          <span className="onboarding-brand">Mark-I</span>
          <span>Step {step + 1} of 3</span>
        </header>

        <div className="onboarding-progress" aria-label={`Step ${step + 1} of 3`}>
          {[0, 1, 2].map((index) => (
            <span key={index} data-active={index <= step} />
          ))}
        </div>

        <form className="onboarding-form" onSubmit={submit}>
          {step === 0 ? (
            <section className="onboarding-step" aria-labelledby="goal-title">
              <h1 id="goal-title">What are you working toward?</h1>
              <p>
                Mark-I uses this goal to decide which skills, patterns, and opportunities matter to you.
              </p>
              <label className="field">
                <span>Your development goal</span>
                <textarea
                  value={goal}
                  onChange={(event) => setGoal(event.target.value)}
                  placeholder="For example: land a junior backend role in three months"
                  rows={4}
                  maxLength={280}
                  autoFocus
                />
                <span className="field__hint">{goal.length}/280 characters</span>
              </label>
            </section>
          ) : null}

          {step === 1 ? (
            <section className="onboarding-step" aria-labelledby="intensity-title">
              <h1 id="intensity-title">How direct should your mentor be?</h1>
              <p>This changes notification thresholds and tone. You can change it later.</p>
              <fieldset className="choice-list">
                <legend className="sr-only">Mentor intensity</legend>
                {INTENSITIES.map((option) => (
                  <label key={option.value} className="choice-row">
                    <input
                      type="radio"
                      name="intensity"
                      value={option.value}
                      checked={intensity === option.value}
                      onChange={() => setIntensity(option.value)}
                    />
                    <span>
                      <strong>{option.name}</strong>
                      <small>{option.description}</small>
                    </span>
                  </label>
                ))}
              </fieldset>
            </section>
          ) : null}

          {step === 2 ? (
            <section className="onboarding-step" aria-labelledby="language-title">
              <h1 id="language-title">Choose your preferred language</h1>
              <p>Mark-I will use it for web and Telegram guidance when possible.</p>
              <fieldset className="choice-list choice-list--compact">
                <legend className="sr-only">Preferred language</legend>
                {LANGUAGES.map((option) => (
                  <label key={option.value} className="choice-row">
                    <input
                      type="radio"
                      name="language"
                      value={option.value}
                      checked={language === option.value}
                      onChange={() => setLanguage(option.value)}
                    />
                    <span><strong>{option.name}</strong></span>
                  </label>
                ))}
              </fieldset>
            </section>
          ) : null}

          {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}

          <div className="onboarding-actions">
            {step > 0 ? (
              <button
                type="button"
                className="button button--secondary"
                onClick={previousStep}
                disabled={submitting}
              >
                Back
              </button>
            ) : <span />}

            {step < 2 ? (
              <button type="button" className="button button--primary" onClick={nextStep}>
                Continue
              </button>
            ) : (
              <button type="submit" className="button button--primary" disabled={submitting}>
                {submitting ? "Saving…" : "Finish setup"}
              </button>
            )}
          </div>
        </form>
      </div>
    </main>
  );
}

export default function OnboardingPage() {
  return (
    <RouteGuard mode="onboarding">
      <OnboardingContent />
    </RouteGuard>
  );
}
