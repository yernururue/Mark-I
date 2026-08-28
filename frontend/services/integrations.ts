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

    return fetchApi<IntegrationState>("/integrations");
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

    const { url } = await fetchApi<{ url: string }>("/github/auth-url");
    window.location.assign(url);
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

    await fetchApi<void>("/github/disconnect", { method: "POST" });
    return this.getState(uid);
  },

  async completeGithubConnection(
    uid: string,
    code: string,
  ): Promise<IntegrationState> {
    if (appConfig.dataMode === "local") {
      return this.connectGithub(uid);
    }

    await fetchApi<void>(`/github/callback?code=${encodeURIComponent(code)}`, {
      method: "POST",
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

    return fetchApi<TelegramLinkCode>("/telegram/link", { method: "POST" });
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

    await fetchApi<void>("/telegram/disconnect", { method: "POST" });
    return this.getState(uid);
  },
};
