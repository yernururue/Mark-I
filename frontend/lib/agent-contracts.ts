import { AppError } from "./errors";
import {
  asRecord,
  decodeList,
  enumValue,
  requiredNumber,
  requiredString,
  stringArray,
  timestamp,
} from "./contract-utils";
import type {
  Agent,
  AgentStatus,
  AgentTemplate,
  AgentTone,
  CreateAgentInput,
  UpdateAgentInput,
} from "@/types/models";

export function decodeAgent(value: unknown, documentId?: string): Agent {
  const data = asRecord(value, "agent");
  const id = requiredString(data.agentId ?? data.id ?? documentId, "agent id");

  if (documentId && id !== documentId) {
    throw new AppError(
      "The agent identifier does not match its Firestore document.",
      "invalid-response",
    );
  }

  return {
    id,
    schemaVersion: requiredNumber(
      data.schemaVersion,
      "agent schemaVersion",
      { min: 1, integer: true },
    ),
    name: requiredString(data.name, "agent name"),
    role: requiredString(data.role, "agent role"),
    template: enumValue<AgentTemplate>(data.template, ["mentor", "designer", "custom"], "agent template"),
    objective: requiredString(data.objective, "agent objective"),
    instructions: requiredString(data.instructions, "agent instructions"),
    tone: enumValue<AgentTone>(
      data.tone,
      ["chill", "normal", "brutal", "concise"],
      "agent tone",
    ),
    toolGrants: stringArray(data.toolGrants, "agent tool grants"),
    contextGrants: stringArray(data.contextGrants, "agent context grants"),
    status: enumValue<AgentStatus>(
      data.status,
      ["active", "paused", "archived"],
      "agent status",
    ),
    createdAt: timestamp(data.createdAt, "agent createdAt"),
    updatedAt: timestamp(data.updatedAt, "agent updatedAt"),
  };
}

export function decodeAgentList(value: unknown): Agent[] {
  return decodeList(value, "agents", (item) => decodeAgent(item));
}

export function serializeCreateAgentInput(
  input: CreateAgentInput,
): Record<string, unknown> {
  return { ...normalizeCreateAgentInput(input) };
}

export function serializeUpdateAgentInput(
  input: UpdateAgentInput,
): Record<string, unknown> {
  return { ...normalizeUpdateAgentInput(input) };
}

export function normalizeCreateAgentInput(input: CreateAgentInput): CreateAgentInput {
  const name = input.name.trim();
  const role = input.role.trim();
  const objective = input.objective.trim();
  const instructions = input.instructions.trim();

  if (name.length < 2 || role.length < 2 || objective.length < 10 || instructions.length < 10) {
    throw new AppError(
      "An agent needs a name, role, objective, and clear instructions.",
      "invalid-input",
    );
  }

  return {
    ...input,
    name,
    role,
    objective,
    instructions,
    toolGrants: [...new Set(input.toolGrants)],
    contextGrants: [...new Set(input.contextGrants)],
  };
}

export function normalizeUpdateAgentInput(input: UpdateAgentInput): UpdateAgentInput {
  const customization = {
    ...input,
    ...(input.name !== undefined ? { name: input.name.trim() } : {}),
    ...(input.role !== undefined ? { role: input.role.trim() } : {}),
    ...(input.objective !== undefined ? { objective: input.objective.trim() } : {}),
    ...(input.instructions !== undefined ? { instructions: input.instructions.trim() } : {}),
    ...(input.toolGrants ? { toolGrants: [...new Set(input.toolGrants)] } : {}),
    ...(input.contextGrants ? { contextGrants: [...new Set(input.contextGrants)] } : {}),
  };

  if (customization.name !== undefined && customization.name.length < 2) {
    throw new AppError("An agent name must contain at least two characters.", "invalid-input");
  }
  if (customization.role !== undefined && customization.role.length < 2) {
    throw new AppError("An agent role must contain at least two characters.", "invalid-input");
  }
  if (customization.objective !== undefined && customization.objective.length < 10) {
    throw new AppError("An agent objective must contain at least ten characters.", "invalid-input");
  }
  if (customization.instructions !== undefined && customization.instructions.length < 10) {
    throw new AppError("Agent instructions must contain at least ten characters.", "invalid-input");
  }

  return customization;
}
