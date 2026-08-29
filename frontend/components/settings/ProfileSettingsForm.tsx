"use client";

import { useState, type FormEvent } from "react";
import type {
  Intensity,
  OnboardingInput,
  PreferredLanguage,
  UserProfile,
} from "@/types/models";

interface ProfileSettingsFormProps {
  profile: UserProfile;
  saving: boolean;
  onSave: (input: OnboardingInput) => Promise<void>;
}

export default function ProfileSettingsForm({
  profile,
  saving,
  onSave,
}: ProfileSettingsFormProps) {
  const [goal, setGoal] = useState(profile.goal);
  const [intensity, setIntensity] = useState<Intensity>(profile.intensity);
  const [language, setLanguage] = useState<PreferredLanguage>(profile.language);
  const [validationError, setValidationError] = useState<string | null>(null);

  const submit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (goal.trim().length < 10) {
      setValidationError("Describe a concrete goal in at least ten characters.");
      return;
    }
    setValidationError(null);
    void onSave({ goal: goal.trim(), intensity, language });
  };

  return (
    <form id="general" className="form-stack" onSubmit={submit}>
      <div className="settings-card settings-rows">
        <div className="settings-row">
          <label htmlFor="profile-goal">Goal</label>
          <textarea
            id="profile-goal"
            rows={2}
            maxLength={280}
            value={goal}
            onChange={(event) => setGoal(event.target.value)}
          />
        </div>
      </div>

      <div className="settings-card settings-rows">
        <div className="settings-row">
          <label htmlFor="profile-intensity">Notification behavior</label>
          <select
            id="profile-intensity"
            value={intensity}
            onChange={(event) => setIntensity(event.target.value as Intensity)}
          >
            <option value="chill">Chill</option>
            <option value="normal">Normal</option>
            <option value="brutal">Brutal</option>
          </select>
        </div>

        <div className="settings-row">
          <label htmlFor="profile-language">Preferred language</label>
          <select
            id="profile-language"
            value={language}
            onChange={(event) => setLanguage(event.target.value as PreferredLanguage)}
          >
            <option value="en">English</option>
            <option value="ru">Русский</option>
            <option value="kk">Қазақша</option>
          </select>
        </div>

        {validationError ? (
          <div className="settings-row">
            <p className="form-message form-message--error" role="alert">{validationError}</p>
          </div>
        ) : null}

        <div className="settings-row settings-row--actions">
          <button type="submit" className="button button--primary" disabled={saving}>
            {saving ? "Saving…" : "Save profile"}
          </button>
        </div>
      </div>
    </form>
  );
}

