"use client";

import { useCallback, useEffect, useState } from "react";
import { getErrorMessage } from "@/lib/errors";
import { subscribeDashboard } from "@/services/dashboard";
import type { DashboardSnapshot } from "@/types/models";

const EMPTY_DASHBOARD: DashboardSnapshot = {
  profile: null,
  observations: [],
  decisions: [],
};

export function useDashboardData(uid: string | undefined) {
  const [data, setData] = useState<DashboardSnapshot>(EMPTY_DASHBOARD);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [revision, setRevision] = useState(0);

  const retry = useCallback(() => {
    setLoading(true);
    setError(null);
    setRevision((value) => value + 1);
  }, []);

  useEffect(() => {
    if (!uid) return;

    return subscribeDashboard(
      uid,
      (snapshot) => {
        setData(snapshot);
        setError(null);
        setLoading(false);
      },
      (subscriptionError) => {
        setError(
          getErrorMessage(
            subscriptionError,
            "Dashboard data could not be loaded.",
          ),
        );
        setLoading(false);
      },
    );
  }, [revision, uid]);

  return { ...data, loading, error, retry };
}
