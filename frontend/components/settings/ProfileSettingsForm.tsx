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
    <form className="settings-section form-stack" onSubmit={submit}>
      <div className="settings-section__heading">
        <h2>Mentor profile</h2>
        <p>These settings shape recommendations, notification thresholds, and tone.</p>
      </div>

      <label className="field">
        <span>Development goal</span>
        <textarea
          rows={4}
          maxLength={280}
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
        />
      </label>

      <div className="settings-fields">
        <label className="field">
          <span>Mentor intensity</span>
          <select
            value={intensity}
            onChange={(event) => setIntensity(event.target.value as Intensity)}
          >
            <option value="chill">Chill</option>
            <option value="normal">Normal</option>
            <option value="brutal">Brutal</option>
          </select>
        </label>

        <label className="field">
          <span>Preferred language</span>
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value as PreferredLanguage)}
          >
            <option value="en">English</option>
            <option value="ru">Русский</option>
            <option value="kk">Қазақша</option>
          </select>
        </label>
      </div>

      {validationError ? (
        <p className="form-message form-message--error" role="alert">{validationError}</p>
      ) : null}

      <div className="settings-section__actions">
        <button type="submit" className="button button--primary" disabled={saving}>
          {saving ? "Saving…" : "Save profile"}
        </button>
      </div>
    </form>
  );
}
