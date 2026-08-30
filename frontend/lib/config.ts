export type DataMode = "local" | "firebase";

const configuredMode = process.env.NEXT_PUBLIC_DATA_MODE;
const configuredApiBaseUrl = process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "");

function resolveDataMode(): DataMode {
  if (configuredMode === "local") {
    if (process.env.NODE_ENV === "production") {
      throw new Error(
        "NEXT_PUBLIC_DATA_MODE=local is not allowed in a production build.",
      );
    }

    return "local";
  }

  if (configuredMode === "firebase" || configuredMode === undefined) {
    return "firebase";
  }

  throw new Error(
    "NEXT_PUBLIC_DATA_MODE must be either \"local\" or \"firebase\".",
  );
}

const dataMode = resolveDataMode();

if (
  process.env.NODE_ENV === "production" &&
  dataMode === "firebase" &&
  !configuredApiBaseUrl
) {
  throw new Error(
    "NEXT_PUBLIC_API_URL is required for a production Firebase build.",
  );
}

export const appConfig = {
  apiBaseUrl: configuredApiBaseUrl,
  dataMode,
  telegramBotUsername:
    process.env.NEXT_PUBLIC_TELEGRAM_BOT_USERNAME ?? "mark_i_bot",
} satisfies {
  apiBaseUrl: string | undefined;
  dataMode: DataMode;
  telegramBotUsername: string;
};

export function getApiBaseUrl(): string {
  if (!appConfig.apiBaseUrl) {
    throw new Error(
      "NEXT_PUBLIC_API_URL is required when NEXT_PUBLIC_DATA_MODE=firebase.",
    );
  }

  return appConfig.apiBaseUrl;
}
