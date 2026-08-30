export class AppError extends Error {
  constructor(
    message: string,
    public readonly code = "unknown",
    public readonly status?: number,
  ) {
    super(message);
    this.name = "AppError";
  }
}

export function getErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return fallback;
}

export function backendContractUnavailable(
  capability: string,
  requirement: string,
): AppError {
  return new AppError(
    `${capability} is unavailable in remote mode. The backend must provide ${requirement}.`,
    "backend-contract",
    503,
  );
}
