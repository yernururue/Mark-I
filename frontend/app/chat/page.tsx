"use client";

import AppShell from "@/components/AppShell";
import RouteGuard from "@/components/RouteGuard";
import ChatPanel from "@/components/chat/ChatPanel";
import { useAuth } from "@/contexts/AuthContext";

function ChatContent() {
  const { user } = useAuth();
  if (!user) return null;
  return <ChatPanel uid={user.uid} />;
}

export default function ChatPage() {
  return (
    <RouteGuard>
      <AppShell>
        <ChatContent />
      </AppShell>
    </RouteGuard>
  );
}
