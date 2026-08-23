import { Decision } from '@/hooks/useDashboardData';
import { Bell, BellOff, Info } from 'lucide-react';

interface DecisionLogProps {
  decisions: Decision[];
}

export default function DecisionLog({ decisions }: DecisionLogProps) {
  if (decisions.length === 0) {
    return (
      <div className="h-full flex flex-col">
        <div className="flex items-center gap-2 mb-4">
          <h3 className="text-lg font-serif italic text-white/80">Decision Engine</h3>
          <Info className="w-4 h-4 text-white/40" />
        </div>
        <div className="flex-1 flex items-center justify-center border border-white/5 bg-white/[0.02] rounded-md p-6">
          <p className="text-white/40 text-sm font-sans text-center">
            No agent decisions made yet. The agent is quietly observing.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center gap-2 mb-4">
        <h3 className="text-lg font-serif italic text-white/80">Decision Engine</h3>
        <Info className="w-4 h-4 text-white/40 cursor-help" title="Shows why the AI mentor decided to contact you or stay silent." />
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent">
        {decisions.map((dec) => {
          const notified = dec.action_taken === 'notify';
          
          return (
            <div 
              key={dec.id} 
              className={`p-4 border rounded-md transition-colors ${
                notified 
                  ? 'border-[#f05638]/30 bg-[#f05638]/5' 
                  : 'border-white/10 bg-white/5 opacity-80'
              }`}
            >
              <div className="flex items-start gap-3">
                <div className={`mt-1 ${notified ? 'text-[#f05638]' : 'text-white/40'}`}>
                  {notified ? <Bell className="w-4 h-4" /> : <BellOff className="w-4 h-4" />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between gap-2 mb-1">
                    <span className={`text-xs font-mono uppercase tracking-wider ${notified ? 'text-[#f05638]' : 'text-white/50'}`}>
                      {notified ? 'NOTIFIED' : 'SILENT'}
                    </span>
                    <span className="text-xs text-white/30">
                      {new Date(dec.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  
                  <p className="text-sm text-white/90 font-sans mb-2 font-medium">
                    Trigger: {dec.trigger}
                  </p>
                  
                  <div className="text-xs text-white/60 bg-black/20 p-2 rounded border border-white/5 font-mono">
                    <span className="text-white/40">Reason: </span>
                    {dec.reason}
                    <div className="mt-1 flex items-center gap-3">
                      <span>Score: {dec.significance_score}</span>
                      <span>Threshold: {dec.threshold}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
