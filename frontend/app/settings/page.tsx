"use client";

import { useState } from "react";
import { Check, Copy, GitBranch, Send } from "lucide-react";
import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import ProfileSettingsForm from "@/components/settings/ProfileSettingsForm";
import { useAuth } from "@/contexts/AuthContext";
import { useSettings } from "@/hooks/useSettings";
import { appConfig } from "@/lib/config";

function SettingsContent() {
  const { user } = useAuth();
  const {
    profile,
    integrations,
    telegramCode,
    loading,
    saving,
    error,
    notice,
    retry,
    saveProfile,
    connectGithub,
    disconnectGithub,
    createTelegramLink,
    disconnectTelegram,
  } = useSettings(user?.uid);
  const [copied, setCopied] = useState(false);

  if (loading) return <RouteState title="Loading settings" />;
  if (!profile || !integrations) {
    return (
      <RouteState
        title="Settings unavailable"
        message={error ?? "Your profile could not be loaded."}
        onRetry={retry}
      />
    );
  }

  const copyCode = async () => {
    if (!telegramCode) return;
    await navigator.clipboard.writeText(telegramCode.code);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="page-content settings-page">
      <header className="page-header">
        <div>
          <h1>Settings</h1>
          <p>Manage how Mark-I learns from your work and contacts you.</p>
        </div>
      </header>

      {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}
      {notice ? <p className="form-message form-message--success" role="status">{notice}</p> : null}

      <ProfileSettingsForm profile={profile} saving={saving} onSave={saveProfile} />

      <section id="integrations" className="settings-section">
        <div className="settings-section__heading">
          <h2>Integrations</h2>
          <p>Connect only the services Mark-I needs for observation and delivery.</p>
        </div>

        <div className="integration-list">
          <article className="integration-row">
            <GitBranch size={22} aria-hidden="true" />
            <div className="integration-row__body">
              <h3>GitHub</h3>
              <p>
                {integrations.github.status === "connected"
                  ? `Connected as ${integrations.github.accountName ?? "GitHub user"}. ${integrations.github.repositoryCount} repositories selected.`
                  : "Connect repositories so Mark-I can observe coding activity."}
              </p>
            </div>
            <button
              type="button"
              className="button button--secondary"
              disabled={saving}
              onClick={() => void (
                integrations.github.status === "connected"
                  ? disconnectGithub()
                  : connectGithub()
              )}
            >
              {integrations.github.status === "connected" ? "Disconnect" : "Connect GitHub"}
            </button>
          </article>

          <article className="integration-row">
            <Send size={22} aria-hidden="true" />
            <div className="integration-row__body">
              <h3>Telegram</h3>
              <p>
                {integrations.telegram.status === "connected"
                  ? `Connected as ${integrations.telegram.accountName ?? "Telegram user"}.`
                  : integrations.telegram.status === "pending"
                    ? "Waiting for you to send the link code to the bot."
                    : "Receive important guidance and continue mentor conversations in Telegram."}
              </p>
              {telegramCode ? (
                <div className="telegram-code">
                  <code>{telegramCode.code}</code>
                  <button type="button" onClick={copyCode} aria-label="Copy Telegram link code">
                    {copied ? <Check size={16} /> : <Copy size={16} />}
                    {copied ? "Copied" : "Copy"}
                  </button>
                  <span>
                    Send <strong>/link {telegramCode.code}</strong> to{" "}
                    <a
                      href={`https://t.me/${appConfig.telegramBotUsername}`}
                      target="_blank"
                      rel="noreferrer"
                    >
                      @{appConfig.telegramBotUsername}
                    </a>. Code expires at {new Date(telegramCode.expiresAt).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}.
                  </span>
                </div>
              ) : null}
            </div>
            <button
              type="button"
              className="button button--secondary"
              disabled={saving}
              onClick={() => void (
                integrations.telegram.status === "connected"
                  ? disconnectTelegram()
                  : createTelegramLink()
              )}
            >
              {integrations.telegram.status === "connected" ? "Disconnect" : "Generate link code"}
            </button>
          </article>
        </div>

        {appConfig.dataMode === "local" ? (
          <p className="settings-mode-note">
            Local preview mode is active. Integration states are stored in this browser until the backend endpoints are enabled.
          </p>
        ) : null}
      </section>
    </div>
  );
}

export default function SettingsPage() {
  return (
    <RouteGuard>
      <AppShell>
        <SettingsContent />
      </AppShell>
    </RouteGuard>
  );
}
