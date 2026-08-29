"use client";

import RouteGuard from "@/components/RouteGuard";
import ChatPanel from "@/components/chat/ChatPanel";
import { useAuth } from "@/contexts/AuthContext";

function DashboardContent() {
  const { user } = useAuth();
  if (!user) return null;
  return <ChatPanel uid={user.uid} />;
}

export default function DashboardPage() {
  return (
    <RouteGuard>
      <DashboardContent />
    </RouteGuard>
  );
}
