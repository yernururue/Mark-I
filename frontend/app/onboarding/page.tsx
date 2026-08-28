"use client";

import { useRef, useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import RouteGuard from "@/components/RouteGuard";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import { userService } from "@/services/user";
import type { CreateAgentInput, Intensity, OnboardingInput, PreferredLanguage } from "@/types/models";

const INTENSITIES: Array<{ value: Intensity; name: string; description: string }> = [
  { value: "chill", name: "Chill", description: "Only surface high-significance updates." },
  { value: "normal", name: "Normal", description: "Balance useful nudges with quiet observation." },
  { value: "brutal", name: "Brutal", description: "Surface smaller gaps and use a more direct tone." },
];

const TEMPLATES: Array<{
  value: CreateAgentInput["template"];
  name: string;
  description: string;
  defaults: Pick<CreateAgentInput, "name" | "role" | "objective" | "instructions" | "tone" | "toolGrants" | "contextGrants">;
}> = [
  {
    value: "mentor",
    name: "Mentor",
    description: "Observe development activity, track growth, and provide focused guidance.",
    defaults: {
      name: "Code mentor",
      role: "mentor",
      objective: "Help me make measurable progress toward my workspace goal.",
      instructions: "Use evidence from my work, explain tradeoffs, and recommend one clear next action.",
      tone: "normal",
      toolGrants: ["read_workspace", "query_github", "publish_artifact"],
      contextGrants: ["workspace-goal", "github-activity"],
    },
  },
  {
    value: "designer",
    name: "Designer",
    description: "Develop product and interface directions with explicit tradeoffs.",
    defaults: {
      name: "Product designer",
      role: "designer",
      objective: "Improve the product experience and make complex flows understandable.",
      instructions: "Explore strong directions, explain tradeoffs, and publish reviewable design artifacts.",
      tone: "concise",
      toolGrants: ["read_workspace", "publish_artifact"],
      contextGrants: ["workspace-goal"],
    },
  },
  {
    value: "custom",
    name: "Custom",
    description: "Define a specialist role, objective, instructions, and access from scratch.",
    defaults: {
      name: "Research agent",
      role: "researcher",
      objective: "Gather evidence for decisions in this workspace.",
      instructions: "Use only permitted context, cite assumptions, and publish a concise report.",
      tone: "concise",
      toolGrants: ["read_workspace", "publish_artifact"],
      contextGrants: ["workspace-goal"],
    },
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
  const profileCreated = useRef(false);
  const [step, setStep] = useState(0);
  const [goal, setGoal] = useState("");
  const [intensity, setIntensity] = useState<Intensity>("normal");
  const [language, setLanguage] = useState<PreferredLanguage>("en");
  const [agent, setAgent] = useState<CreateAgentInput>({
    template: "mentor",
    ...TEMPLATES[0].defaults,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const chooseTemplate = (template: CreateAgentInput["template"]) => {
    const selected = TEMPLATES.find((item) => item.value === template) ?? TEMPLATES[0];
    setAgent({ template, ...selected.defaults });
    setError(null);
  };

  const nextStep = () => {
    if (step === 0 && goal.trim().length < 10) {
      setError("Describe a concrete workspace goal in at least ten characters.");
      return;
    }
    setError(null);
    setStep((current) => Math.min(current + 1, 3));
  };

  const previousStep = () => {
    setError(null);
    setStep((current) => Math.max(current - 1, 0));
  };

  const submit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!user || submitting) return;
    if (agent.name.trim().length < 2 || agent.objective.trim().length < 10 || agent.instructions.trim().length < 10) {
      setError("Add an agent name, objective, and clear instructions before continuing.");
      return;
    }

    const profileInput: OnboardingInput = { goal: goal.trim(), intensity, language };
    const agentInput: CreateAgentInput = {
      ...agent,
      name: agent.name.trim(),
      role: agent.role.trim(),
      objective: agent.objective.trim(),
      instructions: agent.instructions.trim(),
    };
    setSubmitting(true);
    setError(null);

    try {
      if (!profileCreated.current) {
        await userService.submitOnboarding(user.uid, profileInput, {
          displayName: user.displayName,
          email: user.email,
        });
        profileCreated.current = true;
      }
      await agentsService.createAgent(user.uid, agentInput);
      router.replace("/dashboard");
    } catch (submissionError) {
      setError(getErrorMessage(submissionError, "Your workspace setup could not be saved. Please try again."));
      setSubmitting(false);
    }
  };

  return (
    <main className="onboarding-page">
      <div className="onboarding-frame">
        <header className="onboarding-header">
          <span className="onboarding-brand">Mark-I</span>
          <span>Step {step + 1} of 4</span>
        </header>

        <div className="onboarding-progress" aria-label={`Step ${step + 1} of 4`}>
          {[0, 1, 2, 3].map((index) => <span key={index} data-active={index <= step} />)}
        </div>

        <form className="onboarding-form" onSubmit={submit}>
          {step === 0 ? (
            <section className="onboarding-step" aria-labelledby="goal-title">
              <h1 id="goal-title">What should this workspace help you accomplish?</h1>
              <p>Agents may have separate objectives, but this gives the whole workspace a shared direction.</p>
              <label className="field">
                <span>Workspace goal</span>
                <textarea value={goal} onChange={(event) => setGoal(event.target.value)} placeholder="For example: ship and validate our developer tool MVP" rows={4} maxLength={280} autoFocus />
                <span className="field__hint">{goal.length}/280 characters</span>
              </label>
            </section>
          ) : null}

          {step === 1 ? (
            <section className="onboarding-step" aria-labelledby="defaults-title">
              <h1 id="defaults-title">Set workspace defaults</h1>
              <p>These defaults can be overridden for each agent.</p>
              <fieldset className="choice-list">
                <legend>Default notification behavior</legend>
                {INTENSITIES.map((option) => (
                  <label key={option.value} className="choice-row">
                    <input type="radio" name="intensity" checked={intensity === option.value} onChange={() => setIntensity(option.value)} />
                    <span><strong>{option.name}</strong><small>{option.description}</small></span>
                  </label>
                ))}
              </fieldset>
              <label className="field">
                <span>Preferred language</span>
                <select value={language} onChange={(event) => setLanguage(event.target.value as PreferredLanguage)}>
                  {LANGUAGES.map((option) => <option key={option.value} value={option.value}>{option.name}</option>)}
                </select>
              </label>
            </section>
          ) : null}

          {step === 2 ? (
            <section className="onboarding-step" aria-labelledby="template-title">
              <h1 id="template-title">Create your first agent</h1>
              <p>Templates provide editable defaults. They do not lock the agent into a separate product path.</p>
              <fieldset className="template-grid">
                <legend className="sr-only">Agent template</legend>
                {TEMPLATES.map((template) => (
                  <label key={template.value} className="template-option">
                    <input type="radio" name="template" checked={agent.template === template.value} onChange={() => chooseTemplate(template.value)} />
                    <strong>{template.name}</strong>
                    <span>{template.description}</span>
                  </label>
                ))}
              </fieldset>
            </section>
          ) : null}

          {step === 3 ? (
            <section className="onboarding-step" aria-labelledby="agent-title">
              <h1 id="agent-title">Configure {agent.name}</h1>
              <p>Identity, scope, and instructions stay attached to this agent across chat, runs, and outputs.</p>
              <div className="settings-fields">
                <label className="field"><span>Agent name</span><input value={agent.name} onChange={(event) => setAgent((current) => ({ ...current, name: event.target.value }))} /></label>
                <label className="field"><span>Role</span><input value={agent.role} onChange={(event) => setAgent((current) => ({ ...current, role: event.target.value }))} /></label>
              </div>
              <label className="field"><span>Objective</span><textarea rows={2} value={agent.objective} onChange={(event) => setAgent((current) => ({ ...current, objective: event.target.value }))} /></label>
              <label className="field"><span>Instructions</span><textarea rows={3} value={agent.instructions} onChange={(event) => setAgent((current) => ({ ...current, instructions: event.target.value }))} /></label>
              <label className="field"><span>Tone</span><select value={agent.tone} onChange={(event) => setAgent((current) => ({ ...current, tone: event.target.value as CreateAgentInput["tone"] }))}><option value="normal">Normal</option><option value="chill">Chill</option><option value="brutal">Brutal</option><option value="concise">Concise</option></select></label>
              <div className="grant-summary"><span>Tools</span><strong>{agent.toolGrants.join(", ") || "None"}</strong><span>Context</span><strong>{agent.contextGrants.join(", ") || "None"}</strong></div>
            </section>
          ) : null}

          {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
          <div className="onboarding-actions">
            {step > 0 ? <button type="button" className="button button--secondary" onClick={previousStep} disabled={submitting}>Back</button> : <span />}
            {step < 3 ? <button type="button" className="button button--primary" onClick={nextStep}>Continue</button> : <button type="submit" className="button button--primary" disabled={submitting}>{submitting ? "Creating workspace…" : "Create workspace"}</button>}
          </div>
        </form>
      </div>
    </main>
  );
}

export default function OnboardingPage() {
  return <RouteGuard mode="onboarding"><OnboardingContent /></RouteGuard>;
}
