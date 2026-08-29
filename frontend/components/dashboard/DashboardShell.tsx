"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { LogOut, Plus, Settings } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import AgentStatusBadge from "@/components/agents/AgentStatusBadge";
import type { Agent } from "@/types/models";
import type { ReactNode } from "react";

interface DashboardShellProps {
  agents: Agent[];
  children: ReactNode;
  selectedAgentId?: string;
  onSelectAgent?: (agentId: string) => void;
}

export default function DashboardShell({
  agents,
  children,
  selectedAgentId,
  onSelectAgent,
}: DashboardShellProps) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, signOut } = useAuth();
  const accountName = user?.displayName || user?.email || "Mark-I account";
  const visibleAgents = agents.filter((agent) => agent.status !== "archived");

  const handleSignOut = async () => {
    await signOut();
    router.replace("/");
  };

  return (
    <div className="dashboard-shell">
      <a className="skip-link" href="#dashboard-content">Skip to content</a>

      <aside className="chat-roster" aria-label="Agents">
        <div className="chat-roster__brand">
          <Link href="/dashboard" aria-label="Mark-I dashboard">Mark-I</Link>
          <Link href="/agents?create=true" className="icon-button" aria-label="Create agent">
            <Plus size={20} aria-hidden="true" />
          </Link>
        </div>

        <nav className="chat-roster__list">
          {visibleAgents.map((agent) => {
            const selected = selectedAgentId === agent.id;
            return (
              <div className="chat-roster__row" data-selected={selected ? "true" : undefined} key={agent.id}>
                {onSelectAgent ? (
                  <button type="button" onClick={() => onSelectAgent(agent.id)} aria-pressed={selected}>
                    <span>{agent.name}</span><AgentStatusBadge status={agent.status} />
                  </button>
                ) : (
                  <Link className="chat-roster__agent-link" href={`/dashboard?agent=${encodeURIComponent(agent.id)}`}>
                    <span>{agent.name}</span><AgentStatusBadge status={agent.status} />
                  </Link>
                )}
                <Link href={`/agents/${agent.id}`} className="icon-button" aria-label={`Open ${agent.name} settings`}>
                  <Settings size={16} aria-hidden="true" />
                </Link>
              </div>
            );
          })}
        </nav>

        <div className="chat-roster__footer">
          <Link href="/settings" className="chat-roster__settings" aria-current={pathname === "/settings" ? "page" : undefined}>
            <Settings size={17} aria-hidden="true" />
            Settings
          </Link>
          <div className="chat-roster__account">
            <span title={accountName}>{accountName}</span>
            <button type="button" className="icon-button" onClick={handleSignOut} aria-label="Sign out">
              <LogOut size={16} aria-hidden="true" />
            </button>
          </div>
        </div>
      </aside>

      <main id="dashboard-content" className="dashboard-shell__content">{children}</main>
    </div>
  );
}
