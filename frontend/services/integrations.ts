import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import type {
  IntegrationState,
  TelegramLinkCode,
} from "@/types/models";
import {
  getLocalIntegrations,
  saveLocalIntegrations,
} from "./adapters/local-store";

function createLinkCode(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  return Array.from({ length: 6 }, () =>
    alphabet.charAt(Math.floor(Math.random() * alphabet.length)),
  ).join("");
}

export const integrationsService = {
  async getState(uid: string): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      return getLocalIntegrations(uid);
    }

    const profile = await fetchApi<{
      githubConnected: boolean;
      githubUsername?: string;
      connectedRepos?: string[];
      telegramLinked: boolean;
      telegramUsername?: string;
    }>("/me");
    return {
      github: {
        status: profile.githubConnected ? "connected" : "disconnected",
        accountName: profile.githubUsername,
        repositoryCount: profile.connectedRepos?.length ?? 0,
      },
      telegram: {
        status: profile.telegramLinked ? "connected" : "disconnected",
        accountName: profile.telegramUsername,
      },
    };
  },

  async connectGithub(uid: string): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      const current = getLocalIntegrations(uid);
      const next: IntegrationState = {
        ...current,
        github: {
          status: "connected",
          accountName: "Local preview",
          repositoryCount: 0,
        },
      };
      saveLocalIntegrations(uid, next);
      return next;
    }

    const { authUrl } = await fetchApi<{ authUrl: string }>("/github/auth-url");
    window.location.assign(authUrl);
    return this.getState(uid);
  },

  async disconnectGithub(uid: string): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      const current = getLocalIntegrations(uid);
      const next: IntegrationState = {
        ...current,
        github: { status: "disconnected", repositoryCount: 0 },
      };
      saveLocalIntegrations(uid, next);
      return next;
    }

    await fetchApi<void>("/github/disconnect", { method: "DELETE" });
    return this.getState(uid);
  },

  async completeGithubConnection(
    uid: string,
    code: string,
    state: string,
  ): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      return this.connectGithub(uid);
    }

    await fetchApi<void>("/github/callback", {
      method: "POST",
      body: JSON.stringify({ code, state }),
    });
    return this.getState(uid);
  },

  async createTelegramLink(uid: string): Promise<TelegramLinkCode> {
    if (appConfig.dataMode === "local") {
      const code: TelegramLinkCode = {
        code: createLinkCode(),
        expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
      };
      const current = getLocalIntegrations(uid);
      saveLocalIntegrations(uid, {
        ...current,
        telegram: { status: "pending" },
      });
      return code;
    }

    const response = await fetchApi<{ linkCode: string; expiresAt: string }>("/telegram/link", { method: "POST" });
    return { code: response.linkCode, expiresAt: response.expiresAt };
  },

  async disconnectTelegram(uid: string): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      const current = getLocalIntegrations(uid);
      const next: IntegrationState = {
        ...current,
        telegram: { status: "disconnected" },
      };
      saveLocalIntegrations(uid, next);
      return next;
    }

    await fetchApi<void>("/telegram/unlink", { method: "DELETE" });
    return this.getState(uid);
  },
};
