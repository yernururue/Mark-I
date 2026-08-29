import {
  collection,
  onSnapshot,
  orderBy,
  query,
  type Unsubscribe,
} from "firebase/firestore";
import { fetchApi } from "@/lib/api";
import {
  decodeAgent,
  decodeAgentList,
  normalizeCreateAgentInput,
  normalizeUpdateAgentInput,
} from "@/lib/agent-contracts";
import { appConfig } from "@/lib/config";
import { db } from "@/lib/firebase";
import { createId } from "@/lib/id";
import type { Agent, CreateAgentInput, UpdateAgentInput } from "@/types/models";
import {
  getLocalAgents,
  saveLocalAgents,
  subscribeToLocalAgents,
} from "./adapters/local-store";

export const agentsService = {
  subscribeAgents(
    uid: string,
    onData: (agents: Agent[]) => void,
    onError: (error: Error) => void,
  ): Unsubscribe {
    if (appConfig.dataMode === "local") {
      return subscribeToLocalAgents(uid, (agents) => {
        try {
          onData(agents.map((agent) => decodeAgent(agent)));
        } catch (error) {
          onError(
            error instanceof Error
              ? error
              : new Error("Agents could not be decoded."),
          );
        }
      });
    }

    return onSnapshot(
      query(
        collection(db, "users", uid, "agents"),
        orderBy("updatedAt", "desc"),
      ),
      (snapshot) => {
        try {
          onData(snapshot.docs.map((item) => decodeAgent(item.data(), item.id)));
        } catch (error) {
          onError(
            error instanceof Error
              ? error
              : new Error("Agents could not be decoded."),
          );
        }
      },
      onError,
    );
  },

  async getAgents(uid: string): Promise<Agent[]> {
    if (appConfig.dataMode === "local") {
      return getLocalAgents(uid).map((agent) => decodeAgent(agent));
    }

    return decodeAgentList(await fetchApi<unknown>("/agents"));
  },

  async getAgent(uid: string, agentId: string): Promise<Agent> {
    if (appConfig.dataMode === "local") {
      const agent = getLocalAgents(uid).find((item) => item.id === agentId);
      if (!agent) throw new Error("The selected agent is not available.");
      return decodeAgent(agent);
    }
    return decodeAgent(
      await fetchApi<unknown>(`/agents/${encodeURIComponent(agentId)}`),
      agentId,
    );
  },

  async createAgent(uid: string, input: CreateAgentInput): Promise<Agent> {
    const normalizedInput = normalizeCreateAgentInput(input);

    if (appConfig.dataMode === "local") {
      const timestamp = new Date().toISOString();
      const agent: Agent = {
        ...normalizedInput,
        id: createId("agent"),
        status: "active",
        createdAt: timestamp,
        updatedAt: timestamp,
      };
      saveLocalAgents(uid, [agent, ...getLocalAgents(uid)]);
      return decodeAgent(agent);
    }
    return decodeAgent(await fetchApi<unknown>("/agents", {
      method: "POST",
      body: JSON.stringify(normalizedInput),
    }));
  },

  async updateAgent(
    uid: string,
    agentId: string,
    input: UpdateAgentInput,
  ): Promise<Agent> {
    const normalizedInput = normalizeUpdateAgentInput(input);

    if (appConfig.dataMode === "local") {
      const agents = getLocalAgents(uid);
      const current = agents.find((item) => item.id === agentId);
      if (!current) throw new Error("The selected agent is not available.");
      const next: Agent = {
        ...current,
        ...normalizedInput,
        id: current.id,
        updatedAt: new Date().toISOString(),
      };
      saveLocalAgents(uid, agents.map((item) => item.id === agentId ? next : item));
      return decodeAgent(next);
    }
    return decodeAgent(await fetchApi<unknown>(`/agents/${encodeURIComponent(agentId)}`, {
      method: "PATCH",
      body: JSON.stringify(normalizedInput),
    }), agentId);
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
