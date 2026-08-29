import type { Agent } from "@/types/models";

export default function AgentStatusBadge({ status }: { status: Agent["status"] }) {
  if (status !== "paused") return null;
  return <span className="agent-status-badge">Paused</span>;
}
