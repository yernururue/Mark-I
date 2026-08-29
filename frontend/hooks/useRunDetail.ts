"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { agentsService } from "@/services/agents";
import { runsService } from "@/services/runs";
import type { Agent, AgentRun, Artifact } from "@/types/models";

interface RunDetailState {
  agent: Agent | null;
  agents: Agent[];
  artifacts: Artifact[];
  loading: boolean;
  error: string | null;
  run: AgentRun | null;
}

const EMPTY_STATE: RunDetailState = {
  agent: null,
  agents: [],
  artifacts: [],
  loading: true,
  error: null,
  run: null,
};

export function useRunDetail(uid: string | undefined, runId: string | undefined) {
  const [state, setState] = useState<RunDetailState>(EMPTY_STATE);
  const [revision, setRevision] = useState(0);

  const retry = useCallback(() => {
    setState((current) => ({ ...current, loading: true, error: null }));
    setRevision((current) => current + 1);
  }, []);

  useEffect(() => {
    if (!uid || !runId) return;
    let cancelled = false;

    const load = async () => {
      try {
        const [run, agents] = await Promise.all([
          runsService.getRun(uid, runId),
          agentsService.getAgents(uid),
        ]);
        const artifacts = await Promise.all(
          run.artifactIds.map((artifactId) =>
            runsService.getArtifact(uid, artifactId),
          ),
        );
        if (cancelled) return;

        setState({
          agent: agents.find((item) => item.id === run.agentId) ?? null,
          agents,
          artifacts,
          loading: false,
          error: null,
          run,
        });
      } catch (error) {
        if (!cancelled) {
          setState((current) => ({
            ...current,
            loading: false,
            error: getErrorMessage(error, "The run could not be loaded."),
          }));
        }
      }
    };

    void load();
    return () => {
      cancelled = true;
    };
  }, [revision, runId, uid]);

  return { ...state, retry };
}
