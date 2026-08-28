import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import type { Agent } from "@/types/models";

const MARK_I_MENTOR: Agent = {
  id: "mark-i-mentor",
  name: "Mark-I mentor",
  description: "Your developer growth mentor",
  status: "available",
};

export const agentsService = {
  async getAgents(): Promise<Agent[]> {
    if (appConfig.dataMode === "local") {
      return [MARK_I_MENTOR];
    }

    return fetchApi<Agent[]>("/agents");
  },

  async getAgent(agentId: string): Promise<Agent> {
    if (appConfig.dataMode === "local") {
      if (agentId !== MARK_I_MENTOR.id) {
        throw new Error("The selected mentor is not available.");
      }
      return MARK_I_MENTOR;
    }

    return fetchApi<Agent>(`/agents/${encodeURIComponent(agentId)}`);
  },
};
