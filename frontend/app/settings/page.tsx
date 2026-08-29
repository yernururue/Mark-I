"use client";

import { useState } from "react";
import { Check, Copy, GitBranch, Plug, Send, Settings2 } from "lucide-react";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import ProfileSettingsForm from "@/components/settings/ProfileSettingsForm";
import SettingsScaffold from "@/components/settings/SettingsScaffold";
import { useAuth } from "@/contexts/AuthContext";
import { useSettings } from "@/hooks/useSettings";
import { appConfig } from "@/lib/config";

const SETTINGS_NAV = [
  { id: "general", label: "General", icon: Settings2 },
  { id: "integrations", label: "Integrations", icon: Plug },
];

function SettingsPanel() {
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
    <>
    <SettingsScaffold title="General Settings" items={SETTINGS_NAV} closeHref="/dashboard">
      {error ? <p className="form-message form-message--error" role="alert">{error}</p> : null}

      <section className="settings-group">
        <h2>Defaults</h2>
        <ProfileSettingsForm profile={profile} saving={saving} onSave={saveProfile} />
      </section>

      <section id="integrations" className="settings-group">
        <h2>Connections</h2>

        <div className="settings-card integration-list">
          <article className="integration-row">
            <GitBranch size={22} aria-hidden="true" />
            <div className="integration-row__body">
              <h3>GitHub</h3>
              <p>
                {integrations.github.status === "connected"
                  ? `Connected as ${integrations.github.accountName ?? "GitHub user"}`
                  : "Not connected"}
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
                  ? `Connected as ${integrations.telegram.accountName ?? "Telegram user"}`
                  : integrations.telegram.status === "pending"
                    ? "Waiting for link"
                    : "Not connected"}
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

      </section>
    </SettingsScaffold>

      {notice ? (
        <div className="toast" role="status" key={notice}>
          {notice}
        </div>
      ) : null}
    </>
  );
}

export default function SettingsPage() {
  return (
    <RouteGuard>
      <SettingsPanel />
    </RouteGuard>
  );
}

