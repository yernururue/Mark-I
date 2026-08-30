import { AppError } from "./errors";

export type UnknownRecord = Record<string, unknown>;

function invalidField(label: string): AppError {
  return new AppError(
    `The ${label} field is missing or invalid.`,
    "invalid-response",
  );
}

export function asRecord(value: unknown, label: string): UnknownRecord {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new AppError(`The ${label} response is invalid.`, "invalid-response");
  }

  return value as UnknownRecord;
}

export function requiredString(value: unknown, label: string): string {
  if (typeof value !== "string" || !value.trim()) {
    throw invalidField(label);
  }

  return value;
}

export function optionalString(
  value: unknown,
  label: string,
): string | undefined {
  if (value === undefined || value === null) return undefined;
  if (typeof value !== "string") throw invalidField(label);
  return value;
}

export function requiredBoolean(value: unknown, label: string): boolean {
  if (typeof value !== "boolean") throw invalidField(label);
  return value;
}

export function requiredNumber(
  value: unknown,
  label: string,
  options: { min?: number; max?: number; integer?: boolean } = {},
): number {
  if (
    typeof value !== "number" ||
    !Number.isFinite(value) ||
    (options.integer && !Number.isInteger(value)) ||
    (options.min !== undefined && value < options.min) ||
    (options.max !== undefined && value > options.max)
  ) {
    throw invalidField(label);
  }

  return value;
}

export function stringArray(value: unknown, label: string): string[] {
  if (!Array.isArray(value) || value.some((item) => typeof item !== "string")) {
    throw invalidField(label);
  }

  return [...new Set(value)];
}

export function enumValue<T extends string>(
  value: unknown,
  allowed: readonly T[],
  label: string,
): T {
  if (typeof value === "string" && allowed.includes(value as T)) {
    return value as T;
  }

  throw invalidField(label);
}

export function optionalEnumValue<T extends string>(
  value: unknown,
  allowed: readonly T[],
  label: string,
): T | undefined {
  if (value === undefined || value === null) return undefined;
  return enumValue(value, allowed, label);
}

export function timestamp(value: unknown, label: string): string {
  let result: string;

  if (typeof value === "string") {
    result = value;
  } else if (
    value &&
    typeof value === "object" &&
    "toDate" in value &&
    typeof value.toDate === "function"
  ) {
    result = value.toDate().toISOString();
  } else {
    throw invalidField(label);
  }

  if (!result || Number.isNaN(Date.parse(result))) {
    throw invalidField(label);
  }

  return result;
}

export function optionalTimestamp(
  value: unknown,
  label: string,
): string | undefined {
  if (value === undefined || value === null) return undefined;
  return timestamp(value, label);
}

export function decodeList<T>(
  value: unknown,
  label: string,
  decodeItem: (item: unknown) => T,
): T[] {
  if (!Array.isArray(value)) {
    throw new AppError(`The ${label} response is invalid.`, "invalid-response");
  }

  return value.map(decodeItem);
}

export function recordOfNumbers(
  value: unknown,
  label: string,
  options: { min?: number; max?: number } = {},
): Record<string, number> {
  if (value === undefined) return {};
  const data = asRecord(value, label);

  return Object.fromEntries(
    Object.entries(data).map(([key, item]) => [
      key,
      requiredNumber(item, `${label}.${key}`, options),
    ]),
  );
}
