import { fetchApi } from "@/lib/api";
import { appConfig } from "@/lib/config";
import { createId } from "@/lib/id";
import type { Agent, CreateAgentInput } from "@/types/models";
import { getLocalAgents, saveLocalAgents } from "./adapters/local-store";

export const agentsService = {
  async getAgents(uid: string): Promise<Agent[]> {
    if (appConfig.dataMode === "local") return getLocalAgents(uid);
    return fetchApi<Agent[]>("/agents");
  },

  async getAgent(uid: string, agentId: string): Promise<Agent> {
    if (appConfig.dataMode === "local") {
      const agent = getLocalAgents(uid).find((item) => item.id === agentId);
      if (!agent) throw new Error("The selected agent is not available.");
      return agent;
    }
    return fetchApi<Agent>(`/agents/${encodeURIComponent(agentId)}`);
  },

  async createAgent(uid: string, input: CreateAgentInput): Promise<Agent> {
    if (appConfig.dataMode === "local") {
      const timestamp = new Date().toISOString();
      const agent: Agent = {
        ...input,
        id: createId("agent"),
        status: "active",
        createdAt: timestamp,
        updatedAt: timestamp,
      };
      saveLocalAgents(uid, [agent, ...getLocalAgents(uid)]);
      return agent;
    }
    return fetchApi<Agent>("/agents", {
      method: "POST",
      body: JSON.stringify(input),
    });
  },

  async updateAgent(
    uid: string,
    agentId: string,
    input: Partial<CreateAgentInput> & { status?: Agent["status"] },
  ): Promise<Agent> {
    if (appConfig.dataMode === "local") {
      const agents = getLocalAgents(uid);
      const current = agents.find((item) => item.id === agentId);
      if (!current) throw new Error("The selected agent is not available.");
      const next: Agent = {
        ...current,
        ...input,
        id: current.id,
        updatedAt: new Date().toISOString(),
      };
      saveLocalAgents(uid, agents.map((item) => item.id === agentId ? next : item));
      return next;
    }
    return fetchApi<Agent>(`/agents/${encodeURIComponent(agentId)}`, {
      method: "PATCH",
      body: JSON.stringify(input),
    });
  },

  async duplicateAgent(uid: string, agentId: string): Promise<Agent> {
    const source = await this.getAgent(uid, agentId);
    return this.createAgent(uid, {
      name: `${source.name} copy`,
      role: source.role,
      template: source.template,
      objective: source.objective,
      instructions: source.instructions,
      tone: source.tone,
      toolGrants: [...source.toolGrants],
      contextGrants: [...source.contextGrants],
    });
  },
};
