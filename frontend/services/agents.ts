import {
  collection,
  doc,
  getDoc,
  getDocs,
  onSnapshot,
  orderBy,
  query,
} from "firebase/firestore";
import {
  decodeAgent,
  decodeAgentList,
  serializeCreateAgentInput,
  serializeUpdateAgentInput,
} from "@/lib/agent-contracts";
import { appConfig } from "@/lib/config";
import { backendContractUnavailable } from "@/lib/errors";
import { db } from "@/lib/firebase";
import { createId } from "@/lib/id";
import type { Agent } from "@/types/models";
import {
  getLocalAgents,
  saveLocalAgents,
  subscribeToLocalAgents,
} from "./adapters/local-store";
import type { AgentRepository } from "./repository-contracts";

function localAgents(uid: string): Agent[] {
  return decodeAgentList(getLocalAgents(uid));
}

const localAgentRepository: AgentRepository = {
  subscribeAgents(uid, onData, onError) {
    return subscribeToLocalAgents(
      uid,
      (value) => {
        try {
          onData(decodeAgentList(value));
        } catch (error) {
          onError(error instanceof Error ? error : new Error("Agents could not be decoded."));
        }
      },
      onError,
    );
  },

  async getAgents(uid) {
    return localAgents(uid);
  },

  async getAgent(uid, agentId) {
    const agent = localAgents(uid).find((item) => item.id === agentId);
    if (!agent) throw new Error("The selected agent is not available.");
    return agent;
  },

  async createAgent(uid, input) {
    const timestamp = new Date().toISOString();
    const agent = decodeAgent({
      ...serializeCreateAgentInput(input),
      id: createId("agent"),
      schemaVersion: 1,
      status: "active",
      createdAt: timestamp,
      updatedAt: timestamp,
    });
    saveLocalAgents(uid, [agent, ...localAgents(uid)]);
    return agent;
  },

  async updateAgent(uid, agentId, input) {
    const agents = localAgents(uid);
    const current = agents.find((item) => item.id === agentId);
    if (!current) throw new Error("The selected agent is not available.");
    const next = decodeAgent({
      ...current,
      ...serializeUpdateAgentInput(input),
      id: current.id,
      updatedAt: new Date().toISOString(),
    });
    saveLocalAgents(
      uid,
      agents.map((item) => (item.id === agentId ? next : item)),
    );
    return next;
  },
};

const firebaseAgentRepository: AgentRepository = {
  subscribeAgents(uid, onData, onError) {
    return onSnapshot(
      query(
        collection(db, "users", uid, "agents"),
        orderBy("updatedAt", "desc"),
      ),
      (snapshot) => {
        try {
          onData(snapshot.docs.map((item) => decodeAgent(item.data(), item.id)));
        } catch (error) {
          onError(error instanceof Error ? error : new Error("Agents could not be decoded."));
        }
      },
      onError,
    );
  },

  async getAgents(uid) {
    const snapshot = await getDocs(
      query(
        collection(db, "users", uid, "agents"),
        orderBy("updatedAt", "desc"),
      ),
    );
    return snapshot.docs.map((item) => decodeAgent(item.data(), item.id));
  },

  async getAgent(uid, agentId) {
    const snapshot = await getDoc(doc(db, "users", uid, "agents", agentId));
    if (!snapshot.exists()) {
      throw new Error("The selected agent is not available.");
    }
    return decodeAgent(snapshot.data(), snapshot.id);
  },

  async createAgent() {
    throw backendContractUnavailable(
      "Agent creation",
      "an authenticated POST /api/v1/agents endpoint with a validated agent response",
    );
  },

  async updateAgent() {
    throw backendContractUnavailable(
      "Agent updates",
      "an authenticated PATCH /api/v1/agents/{agentId} endpoint with lifecycle support",
    );
  },
};

const agentRepository =
  appConfig.dataMode === "local"
    ? localAgentRepository
    : firebaseAgentRepository;

export const agentsService = {
  subscribeAgents: agentRepository.subscribeAgents.bind(agentRepository),
  getAgents: agentRepository.getAgents.bind(agentRepository),
  getAgent: agentRepository.getAgent.bind(agentRepository),
  createAgent: agentRepository.createAgent.bind(agentRepository),
  updateAgent: agentRepository.updateAgent.bind(agentRepository),

  async duplicateAgent(uid: string, agentId: string): Promise<Agent> {
    const source = await agentRepository.getAgent(uid, agentId);
    return agentRepository.createAgent(uid, {
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
} satisfies AgentRepository & {
  duplicateAgent(uid: string, agentId: string): Promise<Agent>;
};
