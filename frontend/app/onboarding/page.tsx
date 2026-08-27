"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { db } from "@/lib/firebase";
import { collection, addDoc } from "firebase/firestore";
import { Bot, Zap, Cloud, Cpu, Sparkles, Code, Layout, Database, Plug } from "lucide-react";

const ICONS = [
  { id: "bot", icon: Bot, color: "bg-blue-500" },
  { id: "zap", icon: Zap, color: "bg-yellow-500" },
  { id: "cloud", icon: Cloud, color: "bg-cyan-500" },
  { id: "cpu", icon: Cpu, color: "bg-purple-500" },
  { id: "sparkles", icon: Sparkles, color: "bg-pink-500" },
  { id: "code", icon: Code, color: "bg-green-500" },
  { id: "layout", icon: Layout, color: "bg-orange-500" },
  { id: "database", icon: Database, color: "bg-red-500" },
];

export default function Onboarding() {
  const { user, loading } = useAuth();
  const router = useRouter();
  
  const [step, setStep] = useState(0);
  const [agentName, setAgentName] = useState("");
  const [selectedIconId, setSelectedIconId] = useState("bot");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  const handleCreateAgent = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!agentName.trim()) {
      setError("Please enter a name for your agent.");
      return;
    }

    setSubmitting(true);
    setError(null);
    
    try {
      const selectedIcon = ICONS.find(i => i.id === selectedIconId) || ICONS[0];
      
      // Fire and forget - Firestore handles local optimistic updates instantly
      addDoc(collection(db, 'users', user!.uid, 'agents'), {
        name: agentName.trim(),
        icon: selectedIcon.id,
        color: selectedIcon.color,
        timestamp: new Date().toISOString()
      }).catch(err => console.error("Firestore save error:", err));
      
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to create agent");
      setSubmitting(false);
    }
  };

  if (loading || !user) {
    return <div className="min-h-screen bg-[#0A0A0A]"></div>;
  }

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-white flex flex-col items-center justify-center p-6 relative overflow-hidden font-sans">
      {/* Background gradients for visual depth */}
      <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl pointer-events-none"></div>
      <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-purple-500/10 rounded-full blur-3xl pointer-events-none"></div>

      <div className="max-w-xl w-full bg-[#161616] border border-white/5 p-8 rounded-3xl shadow-2xl relative z-10 transition-all duration-500 min-h-[420px] flex flex-col justify-center">
        
        {step === 0 && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-3xl font-medium tracking-tight mb-4">Welcome to Mark-I.</h1>
            <p className="text-white/60 leading-relaxed mb-8 text-[15px]">
              You've just stepped into the future of autonomous workflows. Let's set up your very first AI teammate—an agent you can give real work to.
            </p>
            <button 
              onClick={() => setStep(1)}
              className="bg-white text-black hover:bg-gray-200 px-6 py-3 rounded-full font-medium transition-colors w-full flex justify-center items-center gap-2"
            >
              Continue <span className="text-xl leading-none">&rarr;</span>
            </button>
          </div>
        )}

        {step === 1 && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-2xl font-medium tracking-tight mb-4">What can your Agent do?</h1>
            <div className="space-y-4 mb-8">
              <div className="flex gap-4 items-start bg-white/5 p-4 rounded-2xl">
                <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <Bot className="w-5 h-5 text-blue-400" />
                </div>
                <div>
                  <h3 className="font-medium text-white/90">Autonomous Execution</h3>
                  <p className="text-sm text-white/50 mt-1 leading-relaxed">Agents can browse the web, write code, and execute multi-step plans without supervision.</p>
                </div>
              </div>
              
              <div className="flex gap-4 items-start bg-white/5 p-4 rounded-2xl">
                <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center flex-shrink-0 mt-1">
                  <Plug className="w-5 h-5 text-purple-400" />
                </div>
                <div>
                  <h3 className="font-medium text-white/90">MCP Connectivity</h3>
                  <p className="text-sm text-white/50 mt-1 leading-relaxed">Use the Model Context Protocol (MCP) to seamlessly connect your internal APIs, databases, and tools directly to your agent's brain.</p>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button 
                onClick={() => setStep(0)}
                className="bg-white/5 text-white/80 hover:bg-white/10 px-6 py-3 rounded-full font-medium transition-colors w-1/3"
              >
                Back
              </button>
              <button 
                onClick={() => setStep(2)}
                className="bg-white text-black hover:bg-gray-200 px-6 py-3 rounded-full font-medium transition-colors w-2/3"
              >
                Let's Build One
              </button>
            </div>
          </div>
        )}

        {step === 2 && (
          <div className="animate-in fade-in slide-in-from-bottom-4 duration-500">
            <h1 className="text-2xl font-medium tracking-tight mb-6 text-center">Design Your First Agent</h1>
            
            <form onSubmit={handleCreateAgent} className="space-y-6">
              
              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">Agent Name</label>
                <input 
                  type="text"
                  value={agentName}
                  onChange={(e) => setAgentName(e.target.value)}
                  placeholder="e.g. Deck Designer, Code Reviewer..."
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:outline-none focus:border-white/30 transition-colors"
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-white/70 mb-2">Choose an Icon</label>
                <div className="grid grid-cols-4 gap-3">
                  {ICONS.map((item) => {
                    const IconComp = item.icon;
                    const isSelected = selectedIconId === item.id;
                    return (
                      <div 
                        key={item.id}
                        onClick={() => setSelectedIconId(item.id)}
                        className={`cursor-pointer aspect-square rounded-2xl flex items-center justify-center transition-all ${
                          isSelected ? 'bg-white/10 ring-2 ring-white scale-95 shadow-inner' : 'bg-white/5 hover:bg-white/10'
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-full ${item.color} flex items-center justify-center shadow-lg`}>
                          <IconComp className="w-5 h-5 text-white" />
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              {error && <p className="text-red-400 text-sm">{error}</p>}

              <div className="flex gap-3 pt-2">
                <button 
                  type="button"
                  onClick={() => setStep(1)}
                  className="bg-white/5 text-white/80 hover:bg-white/10 px-6 py-3 rounded-full font-medium transition-colors w-1/3"
                >
                  Back
                </button>
                <button 
                  type="submit"
                  disabled={submitting}
                  className="bg-white text-black hover:bg-gray-200 disabled:opacity-50 px-6 py-3 rounded-full font-medium transition-colors w-2/3 flex items-center justify-center gap-2"
                >
                  {submitting ? "Initializing..." : "Start Chatting"}
                </button>
              </div>

            </form>
          </div>
        )}
        
      </div>
      
      {/* Progress indicators */}
      <div className="flex gap-2 mt-8 z-10">
        {[0, 1, 2].map((i) => (
          <div 
            key={i} 
            className={`h-1.5 rounded-full transition-all duration-300 ${
              step === i ? "w-8 bg-white" : "w-2 bg-white/20"
            }`}
          />
        ))}
      </div>

    </div>
  );
}
