"use client";

import { useMemo, useState } from "react";
import { GitBranch, MessageSquare, Briefcase, Activity } from "lucide-react";
import type { Observation, ObservationSource } from "@/types/models";

interface ObservationFeedProps {
  observations: Observation[];
}

export default function ObservationFeed({ observations }: ObservationFeedProps) {
  const [source, setSource] = useState<ObservationSource | "all">("all");
  const visibleObservations = useMemo(
    () =>
      source === "all"
        ? observations
        : observations.filter((observation) => observation.source === source),
    [observations, source],
  );
  const getIcon = (source: string) => {
    switch (source.toLowerCase()) {
      case 'github':
        return <GitBranch className="w-5 h-5 text-white/70" />;
      case 'chat':
        return <MessageSquare className="w-5 h-5 text-white/70" />;
      case 'opportunity':
        return <Briefcase className="w-5 h-5 text-white/70" />;
      default:
        return <Activity className="w-5 h-5 text-white/70" />;
    }
  };

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment.toLowerCase()) {
      case 'positive':
        return 'text-green-400';
      case 'negative':
        return 'text-red-400';
      default:
        return 'text-white/50';
    }
  };

  if (observations.length === 0) {
    return (
      <div className="panel-empty">
        <h2>Recent activity</h2>
        <div>
          <p>No activity has been recorded yet.</p>
          <span>Connect GitHub or start a mentor conversation to create the first observation.</span>
        </div>
      </div>
    );
  }

  return (
    <section className="activity-panel">
      <div className="panel-heading">
        <h2>Recent activity</h2>
        <div className="filter-tabs" aria-label="Filter activity by source">
          {(["all", "github", "chat", "opportunity"] as const).map((item) => (
            <button
              key={item}
              type="button"
              aria-pressed={source === item}
              onClick={() => setSource(item)}
            >
              {item === "all" ? "All" : item}
            </button>
          ))}
        </div>
      </div>
      <div className="activity-list">
        {visibleObservations.length === 0 ? (
          <p className="activity-list__empty">No {source} activity in this view.</p>
        ) : null}
        {visibleObservations.map((obs) => (
          <article key={obs.id} className="activity-item">
            <div className="activity-item__icon">
                {getIcon(obs.source)}
            </div>
            <div className="activity-item__body">
                <div className="activity-item__meta">
                  <span>
                    {obs.concept}
                  </span>
                  <time dateTime={obs.createdAt}>{new Date(obs.createdAt).toLocaleDateString()}</time>
                </div>
                <p>{obs.summary}</p>
                <div className="activity-item__details">
                  <span className={`text-xs ${getSentimentColor(obs.sentiment)} capitalize`}>
                    {obs.sentiment} sentiment
                  </span>
                  <span>Significance {obs.significanceScore}/10</span>
                </div>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
