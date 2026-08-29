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
