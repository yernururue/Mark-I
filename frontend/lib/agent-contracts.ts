import { AppError } from "./errors";
import type {
  Agent,
  AgentStatus,
  AgentTemplate,
  AgentTone,
  CreateAgentInput,
  UpdateAgentInput,
} from "@/types/models";

type UnknownRecord = Record<string, unknown>;

function asRecord(value: unknown, label: string): UnknownRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new AppError(`The ${label} response is invalid.`, "invalid-response");
  }

  return value as UnknownRecord;
}

function requiredString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw new AppError(`The ${label} field is missing or invalid.`, "invalid-response");
  }

  return value;
}

function optionalString(value: unknown, fallback = ""): string {
  return typeof value === "string" ? value : fallback;
}

function stringArray(value: unknown, label: string): string[] {
  if (value === undefined) return [];
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw new AppError(`The ${label} field is invalid.`, "invalid-response");
  }

  return value;
}

function enumValue<T extends string>(
  value: unknown,
  allowed: readonly T[],
  fallback: T,
  label: string,
): T {
  if (value === undefined) return fallback;
  if (typeof value === "string" && allowed.includes(value as T)) {
    return value as T;
  }

  throw new AppError(`The ${label} field is invalid.`, "invalid-response");
}

function timestamp(value: unknown, label: string): string {
  if (typeof value === "string" && value) return value;
  if (
    value &&
    typeof value === "object" &&
    "toDate" in value &&
    typeof value.toDate === "function"
  ) {
    return value.toDate().toISOString();
  }

  throw new AppError(`The ${label} field is missing or invalid.`, "invalid-response");
}

export function decodeAgent(value: unknown, documentId?: string): Agent {
  const data = asRecord(value, "agent");
  const id = requiredString(data.id ?? documentId, "agent id");

  return {
    id,
    name: requiredString(data.name, "agent name"),
    role: requiredString(data.role, "agent role"),
    template: enumValue<AgentTemplate>(
      data.template,
      ["mentor", "designer", "custom"],
      "custom",
      "agent template",
    ),
    objective: optionalString(data.objective),
    instructions: optionalString(data.instructions),
    tone: enumValue<AgentTone>(
      data.tone,
      ["chill", "normal", "brutal", "concise"],
      "normal",
      "agent tone",
    ),
    toolGrants: stringArray(data.toolGrants, "agent tool grants"),
    contextGrants: stringArray(data.contextGrants, "agent context grants"),
    status: enumValue<AgentStatus>(
      data.status,
      ["active", "paused", "archived"],
      "active",
      "agent status",
    ),
    createdAt: timestamp(data.createdAt, "agent createdAt"),
    updatedAt: timestamp(data.updatedAt, "agent updatedAt"),
  };
}

export function decodeAgentList(value: unknown): Agent[] {
  if (!Array.isArray(value)) {
    throw new AppError("The agents response is invalid.", "invalid-response");
  }

  return value.map((item) => decodeAgent(item));
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
