"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/errors";
import { integrationsService } from "@/services/integrations";

function CallbackContent({ code, state }: { code?: string; state?: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    if (!code || !state) {
      queueMicrotask(() => setError("GitHub did not return a complete authorization response."));
      return;
    }

    let cancelled = false;
    const complete = async () => {
      try {
        await integrationsService.completeGithubConnection(user.uid, code, state);
        if (!cancelled) router.replace("/settings?github=connected");
      } catch (callbackError) {
        if (!cancelled) {
          setError(getErrorMessage(callbackError, "GitHub could not be connected."));
        }
      }
    };
    void complete();
    return () => {
      cancelled = true;
    };
  }, [code, router, state, user]);

  return error ? (
    <RouteState title="GitHub connection failed" message={error} />
  ) : (
    <RouteState title="Connecting GitHub" />
  );
}

export default function GithubCallbackClient({ code, state }: { code?: string; state?: string }) {
  return (
    <RouteGuard>
      <CallbackContent code={code} state={state} />
    </RouteGuard>
  );
}
