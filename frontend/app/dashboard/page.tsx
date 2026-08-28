"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Search, Plus, Mic, Monitor, Cloud, Droplet, Plug, Bot, Zap, Cpu, Sparkles, Code, Layout, Database, Settings } from "lucide-react";
import { useDashboardData } from "@/hooks/useDashboardData";
import CreateAgentModal from "@/components/dashboard/CreateAgentModal";
import SettingsModal from "@/components/dashboard/SettingsModal";

const IconMap: Record<string, any> = {
  bot: Bot,
  zap: Zap,
  cloud: Cloud,
  cpu: Cpu,
  sparkles: Sparkles,
  code: Code,
  layout: Layout,
  database: Database,
};

// Formats timestamp like "9:13 PM"
function formatTime(isoString: string) {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  } catch {
    return "";
  }
}

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const { agents, profile, observations, decisions, loading: dataLoading } = useDashboardData(user?.uid);
  
  const [activeAgentId, setActiveAgentId] = useState<string | null>(null);
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  // Set the first agent as active by default when they load
  useEffect(() => {
    if (agents.length > 0 && !activeAgentId) {
      setActiveAgentId(agents[0].id);
    }
  }, [agents, activeAgentId]);

  if (authLoading || !user || dataLoading) {
    return (
      <div className="min-h-screen bg-[#0A0A0A] flex items-center justify-center">
        <p className="text-white/50 text-sm font-sans animate-pulse">Loading...</p>
      </div>
    );
  }

  const activeAgent = agents.find(a => a.id === activeAgentId) || agents[0];
  const ActiveIcon = activeAgent ? (IconMap[activeAgent.icon] || Bot) : Cloud;
  const activeColor = activeAgent?.color || "bg-blue-500";
  const agentName = activeAgent?.name || "No Agent Found";

  return (
    <div className="flex h-screen w-screen bg-[#0A0A0A] text-[#E0E0E0] font-sans overflow-hidden">
      
      {/* LEFT SIDEBAR */}
      <aside className="w-[280px] flex-shrink-0 bg-[#161616] border-r border-white/5 flex flex-col z-20">
        {/* Header: Search & Add Agent */}
        <div className="flex items-center gap-3 px-4 pt-6 pb-4">
          <div className="flex-1 bg-white/5 rounded-full flex items-center px-3 py-1.5 border border-white/5 focus-within:border-white/20 transition-colors">
            <Search className="w-4 h-4 text-white/40 mr-2 flex-shrink-0" />
            <input 
              type="text" 
              placeholder="Search" 
              className="bg-transparent border-none text-sm w-full outline-none text-white/80 placeholder:text-white/30"
            />
          </div>
          
          <button 
            onClick={() => setIsCreateModalOpen(true)}
            className="flex-shrink-0 w-8 h-8 flex items-center justify-center rounded-full bg-white/5 hover:bg-white/10 text-white/60 hover:text-white transition-colors"
            title="Create new agent"
          >
            <Plus className="w-4 h-4" />
          </button>
        </div>

        {/* Chat List */}
        <div className="flex-1 overflow-y-auto px-2">
          {agents.length === 0 && (
            <div className="p-4 text-center">
              <p className="text-white/40 text-sm mb-4">No agents yet.</p>
              <button 
                onClick={() => setIsCreateModalOpen(true)}
                className="bg-white/10 hover:bg-white/20 text-white px-4 py-2 rounded-lg text-sm transition-colors"
              >
                Create Agent
              </button>
            </div>
          )}

          {agents.map(agent => {
            const isActive = agent.id === activeAgentId;
            const ItemIcon = IconMap[agent.icon] || Bot;
            
            return (
              <div 
                key={agent.id}
                onClick={() => setActiveAgentId(agent.id)}
                className={`flex items-start gap-3 p-2 rounded-xl cursor-pointer mb-1 group transition-colors ${
                  isActive ? 'bg-white/5' : 'hover:bg-white/[0.02]'
                }`}
              >
                <div className={`w-10 h-10 rounded-full ${agent.color} flex items-center justify-center flex-shrink-0`}>
                  <ItemIcon className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1 min-w-0 pt-0.5">
                  <div className="flex justify-between items-baseline mb-0.5">
                    <p className={`text-sm font-medium truncate transition-colors ${
                      isActive ? 'text-white/90' : 'text-white/70 group-hover:text-white/90'
                    }`}>
                      {agent.name}
                    </p>
                    <span className="text-[10px] text-white/40 flex-shrink-0">
                      {formatTime(agent.timestamp)}
                    </span>
                  </div>
                  <p className={`text-xs truncate transition-colors ${
                    isActive ? 'text-white/50' : 'text-white/40 group-hover:text-white/50'
                  }`}>
                    Hello, how can I help you today?
                  </p>
                </div>
              </div>
            );
          })}
        </div>

        {/* Bottom Actions */}
        <div className="p-4 border-t border-white/5 flex flex-col gap-2">
          <button className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 text-sm text-white/70 hover:text-white transition-colors">
            <Plug className="w-4 h-4" />
            Plugins
          </button>
          <button className="flex items-center gap-3 p-2 rounded-xl hover:bg-white/5 text-sm text-white/70 hover:text-white transition-colors">
            <div className="w-5 h-5 rounded-full bg-white/10 flex items-center justify-center text-[10px] uppercase font-medium">
              {user.displayName?.[0] || user.email?.[0] || 'V'}
            </div>
            {user.displayName || user.email || 'Vlad s'}
          </button>
        </div>
      </aside>

      {/* MAIN CHAT AREA */}
      <main className="flex-1 flex flex-col bg-[#0A0A0A] relative">
        {/* Header */}
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-6 flex-shrink-0 z-10">
          {activeAgent ? (
            <div className="flex items-center gap-3">
              <div className={`w-8 h-8 rounded-full ${activeColor} flex items-center justify-center`}>
                <ActiveIcon className="w-4 h-4 text-white" />
              </div>
              <h2 className="text-sm font-medium text-white/80">{agentName}</h2>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded-full bg-white/5"></div>
              <div className="w-24 h-4 bg-white/5 rounded-full"></div>
            </div>
          )}
          <div className="flex items-center gap-2">
            <button className="p-2 rounded-full hover:bg-white/5 transition-colors">
              <Monitor className="w-4 h-4 text-white/40" />
            </button>
            <button 
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 rounded-full hover:bg-white/5 transition-colors"
              title="Dashboard Settings & Analytics"
            >
              <Settings className="w-4 h-4 text-white/40" />
            </button>
          </div>
        </header>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          
          {activeAgent ? (
            <>
              {/* Bot Default Message */}
              <div className="flex justify-start">
                <div className="bg-[#1C1C1C] rounded-2xl rounded-tl-sm p-4 max-w-[80%] text-[15px] text-white/80 leading-relaxed shadow-sm">
                  <p>Hello! I'm <strong>{agentName}</strong>. I was just initialized.</p>
                  <p className="mt-2">How can I help you today?</p>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center opacity-50">
              <p className="text-sm">Select or create an agent to start chatting.</p>
            </div>
          )}

          {/* Spacer for bottom input */}
          <div className="h-24 flex-shrink-0"></div>
        </div>

        {/* Input Area */}
        <div className="absolute bottom-6 left-0 right-0 px-6 mx-auto w-full max-w-4xl">
          <div className="bg-[#1C1C1C] rounded-full flex items-center px-4 py-3.5 shadow-xl border border-white/5 focus-within:border-white/20 transition-colors relative z-10">
            <button className="w-8 h-8 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors flex-shrink-0 text-white/70">
              <Plus className="w-4 h-4" />
            </button>
            <input 
              type="text" 
              placeholder={`Message ${agentName}...`}
              className="bg-transparent border-none text-[15px] w-full outline-none text-white/90 placeholder:text-white/30 px-4"
              disabled={!activeAgent}
            />
            <button className="w-8 h-8 rounded-full bg-white text-black flex items-center justify-center transition-colors flex-shrink-0 hover:bg-gray-200" disabled={!activeAgent}>
              <Mic className="w-4 h-4" />
            </button>
          </div>
          {/* subtle gradient fade behind input to mask scrolling text */}
          <div className="absolute bottom-[-24px] left-0 right-0 h-32 bg-gradient-to-t from-[#0A0A0A] via-[#0A0A0A]/90 to-transparent z-0 pointer-events-none"></div>
        </div>
        
      </main>

      <CreateAgentModal 
        isOpen={isCreateModalOpen} 
        onClose={() => setIsCreateModalOpen(false)} 
      />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        profile={profile}
        observations={observations}
        decisions={decisions}
      />
    </div>
  );
}
