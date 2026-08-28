import { X } from "lucide-react";
import SkillRadar from "./SkillRadar";
import ObservationFeed from "./ObservationFeed";
import DecisionLog from "./DecisionLog";
import { UserProfile, Observation, Decision } from "@/hooks/useDashboardData";

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  profile: UserProfile | null;
  observations: Observation[];
  decisions: Decision[];
}

export default function SettingsModal({ isOpen, onClose, profile, observations, decisions }: SettingsModalProps) {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4 animate-in fade-in duration-200">
      <div 
        className="bg-[#161616] border border-white/5 rounded-3xl shadow-2xl w-full max-w-6xl max-h-[90vh] flex flex-col overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-white/5 flex-shrink-0">
          <h2 className="text-2xl font-medium tracking-tight text-white/90">Dashboard Settings & Analytics</h2>
          <button 
            onClick={onClose}
            className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center text-white/60 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 h-full min-h-[500px]">
            {/* Left Col: Skill Radar */}
            <div className="bg-white/5 border border-white/5 rounded-2xl p-6">
              <SkillRadar skills={profile?.skills} />
            </div>
            
            {/* Middle Col: Observation Feed */}
            <div className="bg-white/5 border border-white/5 rounded-2xl p-6">
              <ObservationFeed observations={observations} />
            </div>

            {/* Right Col: Decision Log */}
            <div className="bg-white/5 border border-white/5 rounded-2xl p-6">
              <DecisionLog decisions={decisions} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
