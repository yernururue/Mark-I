"use client";

import Link from "next/link";
import { ArrowRight, GitBranch, MessageSquare } from "lucide-react";
import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import RouteState from "@/components/RouteState";
import DecisionLog from "@/components/dashboard/DecisionLog";
import ObservationFeed from "@/components/dashboard/ObservationFeed";
import SkillRadar from "@/components/dashboard/SkillRadar";
import { useAuth } from "@/contexts/AuthContext";
import { useDashboardData } from "@/hooks/useDashboardData";

function DashboardContent() {
  const { user } = useAuth();
  const { profile, observations, decisions, loading, error, retry } =
    useDashboardData(user?.uid);

  if (loading) {
    return <RouteState title="Loading your dashboard" />;
  }

  if (error) {
    return (
      <RouteState
        title="Dashboard unavailable"
        message={error}
        onRetry={retry}
      />
    );
  }

  const displayName = user?.displayName?.split(" ")[0];

  return (
    <div className="page-content dashboard-page">
      <header className="page-header">
        <div>
          <h1>{displayName ? `Good to see you, ${displayName}` : "Your growth dashboard"}</h1>
          <p>{profile?.goal || "Set a goal in Settings to focus your mentor."}</p>
        </div>
        <Link href="/chat" className="button button--primary">
          <MessageSquare size={17} aria-hidden="true" />
          Ask your mentor
        </Link>
      </header>

      <section className="dashboard-status" aria-label="Mentor configuration">
        <div>
          <span>Mentor intensity</span>
          <strong>{profile?.intensity ?? "Normal"}</strong>
        </div>
        <div>
          <span>Preferred language</span>
          <strong>{profile?.language?.toUpperCase() ?? "EN"}</strong>
        </div>
        <Link href="/settings">
          Review settings <ArrowRight size={15} aria-hidden="true" />
        </Link>
      </section>

      {observations.length === 0 && Object.keys(profile?.skills ?? {}).length === 0 ? (
        <section className="getting-started" aria-labelledby="getting-started-title">
          <div>
            <GitBranch size={21} aria-hidden="true" />
            <h2 id="getting-started-title">Start with your real work</h2>
            <p>
              Connect GitHub so Mark-I can observe activity and build a skill profile.
              You can still use mentor chat before the backend integration is live.
            </p>
          </div>
          <Link href="/settings#integrations" className="button button--secondary">
            Manage integrations
          </Link>
        </section>
      ) : null}

      <div className="dashboard-grid">
        <SkillRadar skills={profile?.skills} />
        <ObservationFeed observations={observations} />
        <DecisionLog decisions={decisions} />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <RouteGuard>
      <AppShell>
        <DashboardContent />
      </AppShell>
    </RouteGuard>
  );
}
