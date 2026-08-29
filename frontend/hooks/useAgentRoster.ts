"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import type { Agent } from "@/types/models";

export function useAgentRoster(uid: string | undefined) {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (!uid) return;
    let cancelled = false;

    agentsService.getAgents(uid)
      .then((items) => {
        if (cancelled) return;
        setAgents(items.filter((agent) => agent.status !== "archived"));
        setError(null);
      })
      .catch((loadError) => {
        if (!cancelled) setError(getErrorMessage(loadError, "Agents could not be loaded."));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [revision, uid]);

  return { agents, loading, error, retry };
}
