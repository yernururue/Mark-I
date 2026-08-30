import { getApiBaseUrl } from "./config";
import { AppError } from "./errors";
import { auth } from "./firebase";

interface DecodedApiError {
  code: string;
  message: string;
}

function decodeApiError(value: unknown): DecodedApiError {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return { code: "api", message: "The request could not be completed." };
  }

  const body = value as Record<string, unknown>;
  const detail =
    body.detail && typeof body.detail === "object" && !Array.isArray(body.detail)
      ? (body.detail as Record<string, unknown>)
      : undefined;
  const nestedError =
    body.error && typeof body.error === "object" && !Array.isArray(body.error)
      ? (body.error as Record<string, unknown>)
      : detail?.error &&
          typeof detail.error === "object" &&
          !Array.isArray(detail.error)
        ? (detail.error as Record<string, unknown>)
        : undefined;

  const message =
    (typeof nestedError?.message === "string" && nestedError.message) ||
    (typeof body.detail === "string" && body.detail) ||
    (typeof body.message === "string" && body.message) ||
    "The request could not be completed.";
  const code =
    (typeof nestedError?.code === "string" && nestedError.code) || "api";

  return { code, message };
}

export async function fetchApi(
  endpoint: string,
  options: RequestInit = {},
): Promise<unknown> {
  await auth.authStateReady();
  const token = await auth.currentUser?.getIdToken();
  if (!token) {
    throw new AppError(
      "Sign in again before contacting the Mark-I service.",
      "unauthenticated",
      401,
    );
  }
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  headers.set("Authorization", `Bearer ${token}`);

  let response: Response;

  try {
    response = await fetch(`${getApiBaseUrl()}${endpoint}`, {
      ...options,
      headers,
    });
  } catch {
    throw new AppError(
      "The Mark-I service could not be reached. Check the API URL and try again.",
      "network",
    );
  }

  if (!response.ok) {
    const errorBody = decodeApiError(await response.json().catch(() => undefined));
    throw new AppError(
      errorBody.message,
      errorBody.code,
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined;
  }

  try {
    return (await response.json()) as unknown;
  } catch {
    throw new AppError(
      "The Mark-I service returned an invalid JSON response.",
      "invalid-response",
      response.status,
    );
  }
}
