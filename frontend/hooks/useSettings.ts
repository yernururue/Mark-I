"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { integrationsService } from "@/services/integrations";
import { userService } from "@/services/user";
import type {
  IntegrationState,
  OnboardingInput,
  TelegramLinkCode,
  UserProfile,
} from "@/types/models";

export function useSettings(uid: string | undefined) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [integrations, setIntegrations] = useState<IntegrationState | null>(null);
  const [telegramCode, setTelegramCode] = useState<TelegramLinkCode | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (!uid) return;
    let cancelled = false;

    const load = async () => {
      try {
        const [nextProfile, nextIntegrations] = await Promise.all([
          userService.getProfile(uid),
          integrationsService.getState(uid),
        ]);
        if (cancelled) return;
        setProfile(nextProfile);
        setIntegrations(nextIntegrations);
        setError(null);
      } catch (loadError) {
        if (!cancelled) {
          setError(getErrorMessage(loadError, "Settings could not be loaded."));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [revision, uid]);

  const runAction = useCallback(
    async (action: () => Promise<IntegrationState>, successMessage: string) => {
      setSaving(true);
      setError(null);
      setNotice(null);
      try {
        const next = await action();
        setIntegrations(next);
        setNotice(successMessage);
      } catch (actionError) {
        setError(getErrorMessage(actionError, "The integration could not be updated."));
      } finally {
        setSaving(false);
      }
    },
    [],
  );

  const saveProfile = useCallback(
    async (input: OnboardingInput) => {
      if (!uid) return;
      setSaving(true);
      setError(null);
      setNotice(null);
      try {
        const next = await userService.updateProfile(uid, input);
        setProfile(next);
        setNotice("Profile settings saved.");
      } catch (saveError) {
        setError(getErrorMessage(saveError, "Profile settings could not be saved."));
      } finally {
        setSaving(false);
      }
    },
    [uid],
  );

  const connectGithub = useCallback(() => {
    if (!uid) return Promise.resolve();
    return runAction(
      () => integrationsService.connectGithub(uid),
      "GitHub connection updated.",
    );
  }, [runAction, uid]);

  const disconnectGithub = useCallback(() => {
    if (!uid) return Promise.resolve();
    return runAction(
      () => integrationsService.disconnectGithub(uid),
      "GitHub disconnected.",
    );
  }, [runAction, uid]);

  const createTelegramLink = useCallback(async () => {
    if (!uid) return;
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      const code = await integrationsService.createTelegramLink(uid);
      setTelegramCode(code);
      setIntegrations(await integrationsService.getState(uid));
    } catch (linkError) {
      setError(getErrorMessage(linkError, "A Telegram link code could not be created."));
    } finally {
      setSaving(false);
    }
  }, [uid]);

  const disconnectTelegram = useCallback(() => {
    if (!uid) return Promise.resolve();
    setTelegramCode(null);
    return runAction(
      () => integrationsService.disconnectTelegram(uid),
      "Telegram disconnected.",
    );
  }, [runAction, uid]);

  return {
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
  };
}
