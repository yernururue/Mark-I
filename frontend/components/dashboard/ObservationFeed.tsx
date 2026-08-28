import { Observation } from '@/hooks/useDashboardData';
import { GitBranch, MessageSquare, Briefcase, Activity } from 'lucide-react';

interface ObservationFeedProps {
  observations: Observation[];
}

export default function ObservationFeed({ observations }: ObservationFeedProps) {
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
      <div className="h-full flex flex-col">
        <h3 className="text-lg font-medium tracking-tight mb-4 text-white/90">Activity Feed</h3>
        <div className="flex-1 flex items-center justify-center border border-white/5 bg-white/[0.02] rounded-md p-6">
          <p className="text-white/40 text-sm font-sans">No activity recorded yet.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <h3 className="text-lg font-medium tracking-tight mb-4 text-white/90">Activity Feed</h3>
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {observations.map((obs) => (
          <div key={obs.id} className="p-4 border border-white/10 bg-white/5 rounded-md hover:bg-white/10 transition-colors">
            <div className="flex items-start gap-3">
              <div className="mt-1 p-2 bg-white/5 rounded-full">
                {getIcon(obs.source)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-xs font-mono text-[#f05638] uppercase tracking-wider">
                    {obs.concept}
                  </span>
                  <span className="text-xs text-white/30">
                    {new Date(obs.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <p className="text-sm text-white/80 font-sans leading-relaxed">
                  {obs.summary}
                </p>
                <div className="mt-2 flex items-center gap-4">
                  <span className={`text-xs ${getSentimentColor(obs.sentiment)} capitalize`}>
                    {obs.sentiment} sentiment
                  </span>
                  <span className="text-xs text-white/40">
                    Sig: {obs.significance_score}/10
                  </span>
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
