import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { backendContractUnavailable } from "@/lib/errors";
import {
  decodeGithubAuthUrl,
  decodeGithubCallback,
  decodeGithubRepositories,
  decodeIntegrationProfile,
  decodeIntegrationState,
  decodeSuccess,
  decodeTelegramLinkCode,
  serializeGithubCallbackCommand,
} from "@/lib/resource-contracts";
import type { IntegrationState } from "@/types/models";
import {
  getLocalIntegrations,
  saveLocalIntegrations,
} from "./adapters/local-store";
import type { IntegrationRepository } from "./repository-contracts";

function createLinkCode(): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789";
  return Array.from({ length: 6 }, () =>
    alphabet.charAt(Math.floor(Math.random() * alphabet.length)),
  ).join("");
}

function localIntegrations(uid: string): IntegrationState {
  return decodeIntegrationState(getLocalIntegrations(uid));
}

const localIntegrationRepository: IntegrationRepository = {
  async getState(uid) {
    return localIntegrations(uid);
  },

  async connectGithub(uid) {
    const current = localIntegrations(uid);
    const next = decodeIntegrationState({
      ...current,
      github: {
        status: "connected",
        accountName: "Local preview",
        repositoryCount: 0,
      },
    });
    saveLocalIntegrations(uid, next);
    return next;
  },

  async disconnectGithub(uid) {
    const current = localIntegrations(uid);
    const next = decodeIntegrationState({
      ...current,
      github: { status: "disconnected", repositoryCount: 0 },
    });
    saveLocalIntegrations(uid, next);
    return next;
  },

  async completeGithubConnection(uid) {
    return this.connectGithub(uid);
  },

  async createTelegramLink(uid) {
    const code = decodeTelegramLinkCode({
      code: createLinkCode(),
      expiresAt: new Date(Date.now() + 10 * 60 * 1000).toISOString(),
    });
    const current = localIntegrations(uid);
    saveLocalIntegrations(
      uid,
      decodeIntegrationState({
        ...current,
        telegram: { status: "pending" },
      }),
    );
    return code;
  },

  async disconnectTelegram(uid) {
    const current = localIntegrations(uid);
    const next = decodeIntegrationState({
      ...current,
      telegram: { status: "disconnected" },
    });
    saveLocalIntegrations(uid, next);
    return next;
  },
};

const firebaseIntegrationRepository: IntegrationRepository = {
  async getState() {
    const profile = await fetchApi("/me");
    const initial = decodeIntegrationProfile(profile, 0);
    if (initial.github.status !== "connected") return initial;

    const repositories = decodeGithubRepositories(
      await fetchApi("/github/repos"),
    );
    return decodeIntegrationProfile(
      profile,
      repositories.filter((repository) => repository.connected).length,
    );
  },

  async connectGithub(uid) {
    const authUrl = decodeGithubAuthUrl(await fetchApi("/github/auth-url"));
    window.location.assign(authUrl);
    return this.getState(uid);
  },

  async disconnectGithub(uid) {
    const response = await fetchApi("/github/disconnect", { method: "DELETE" });
    decodeSuccess(response, "GitHub disconnect");
    return this.getState(uid);
  },

  async completeGithubConnection(uid, code, state) {
    const response = await fetchApi("/github/callback", {
      method: "POST",
      body: JSON.stringify(serializeGithubCallbackCommand(code, state)),
    });
    decodeGithubCallback(response);
    return this.getState(uid);
  },

  async createTelegramLink() {
    throw backendContractUnavailable(
      "Telegram linking",
      "POST /api/v1/telegram/link returning both code and expiresAt",
    );
  },

  async disconnectTelegram(uid) {
    const response = await fetchApi("/telegram/link", { method: "DELETE" });
    decodeSuccess(response, "Telegram disconnect");
    return this.getState(uid);
  },
};

const integrationRepository =
  appConfig.dataMode === "local"
    ? localIntegrationRepository
    : firebaseIntegrationRepository;

export const integrationsService = {
  getState: integrationRepository.getState.bind(integrationRepository),
  connectGithub: integrationRepository.connectGithub.bind(integrationRepository),
  disconnectGithub:
    integrationRepository.disconnectGithub.bind(integrationRepository),
  completeGithubConnection:
    integrationRepository.completeGithubConnection.bind(integrationRepository),
  createTelegramLink:
    integrationRepository.createTelegramLink.bind(integrationRepository),
  disconnectTelegram:
    integrationRepository.disconnectTelegram.bind(integrationRepository),
} satisfies IntegrationRepository;
