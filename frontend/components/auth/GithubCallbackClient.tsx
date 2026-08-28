"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/errors";
import { integrationsService } from "@/services/integrations";

function CallbackContent({ code }: { code?: string }) {
  const { user } = useAuth();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!user) return;
    if (!code) {
      queueMicrotask(() => setError("GitHub did not return an authorization code."));
      return;
    }

    let cancelled = false;
    const complete = async () => {
      try {
        await integrationsService.completeGithubConnection(user.uid, code);
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
  }, [code, router, user]);

  return error ? (
    <RouteState title="GitHub connection failed" message={error} />
  ) : (
    <RouteState title="Connecting GitHub" />
  );
}

export default function GithubCallbackClient({ code }: { code?: string }) {
  return (
    <RouteGuard>
      <CallbackContent code={code} />
    </RouteGuard>
  );
}
