"use client";

import { useCallback, useEffect, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { getErrorMessage } from "@/lib/errors";
import { userService } from "@/services/user";
import RouteState from "./RouteState";

type GuardMode = "authenticated" | "app" | "onboarding";

interface RouteGuardProps {
  children: ReactNode;
  mode?: GuardMode;
}

export default function RouteGuard({
  children,
  mode = "app",
}: RouteGuardProps) {
  const { user, loading: authLoading } = useAuth();
  const pathname = usePathname();
  const router = useRouter();
  const [checking, setChecking] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const retry = useCallback(() => {
    setChecking(true);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (authLoading) return;

    if (!user) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }

    if (mode === "authenticated") {
      queueMicrotask(() => setChecking(false));
      return;
    }

    let cancelled = false;
    const checkOnboarding = async () => {
      try {
        const completed = await userService.getOnboardingStatus(user.uid);
        if (cancelled) return;

        if (mode === "app" && !completed) {
          router.replace("/onboarding");
          return;
        }

        if (mode === "onboarding" && completed) {
          router.replace("/dashboard");
          return;
        }

        setChecking(false);
      } catch (statusError) {
        if (!cancelled) {
          setError(
            getErrorMessage(
              statusError,
              "Your account status could not be checked.",
            ),
          );
          setChecking(false);
        }
      }
    };

    void checkOnboarding();
    return () => {
      cancelled = true;
    };
  }, [authLoading, mode, pathname, revision, router, user]);

  if (authLoading || checking || !user) {
    return <RouteState />;
  }

  if (error) {
    return (
      <RouteState
        title="Account check failed"
        message={error}
        onRetry={retry}
      />
    );
  }

  return children;
}
