import { getApiBaseUrl } from "./config";
import { AppError } from "./errors";
import { auth } from "./firebase";

interface ApiErrorBody {
  detail?: string;
  message?: string;
  error?: {
    code?: string;
    message?: string;
  };
}

export async function fetchApi<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  await auth.authStateReady();
  const token = await auth.currentUser?.getIdToken();
  const headers = new Headers(options.headers);

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }

  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

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
    const errorBody = (await response.json().catch(() => ({}))) as ApiErrorBody;
    throw new AppError(
      errorBody.error?.message ?? errorBody.detail ?? errorBody.message ?? "The request could not be completed.",
      errorBody.error?.code ?? "api",
      response.status,
    );
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
