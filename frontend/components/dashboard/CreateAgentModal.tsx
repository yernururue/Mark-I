"use client";

import { useState } from "react";
import { db } from "@/lib/firebase";
import { collection, addDoc } from "firebase/firestore";
import { useAuth } from "@/contexts/AuthContext";
import { Bot, Zap, Cloud, Cpu, Sparkles, Code, Layout, Database } from "lucide-react";

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

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function CreateAgentModal({ isOpen, onClose }: CreateAgentModalProps) {
  const { user } = useAuth();
  const [agentName, setAgentName] = useState("");
  const [selectedIconId, setSelectedIconId] = useState("bot");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

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
      
      // Fire and forget for instant optimistic UI
      addDoc(collection(db, 'users', user!.uid, 'agents'), {
        name: agentName.trim(),
        icon: selectedIcon.id,
        color: selectedIcon.color,
        timestamp: new Date().toISOString()
      }).catch(err => console.error("Firestore save error:", err));
      
      setAgentName("");
      setSelectedIconId("bot");
      setSubmitting(false);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to create agent");
      setSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div 
        className="bg-[#161616] border border-white/10 w-full max-w-md p-8 relative shadow-2xl rounded-3xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button 
          onClick={onClose}
          className="absolute top-5 right-5 text-white/40 hover:text-white transition-colors p-2"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>

        <h2 className="text-2xl font-medium tracking-tight mb-6 text-center text-white">Create New Agent</h2>
        
        <form onSubmit={handleCreateAgent} className="space-y-6">
          
          <div>
            <label className="block text-sm font-medium text-white/70 mb-2">Agent Name</label>
            <input 
              type="text"
              value={agentName}
              onChange={(e) => setAgentName(e.target.value)}
              placeholder="e.g. Code Reviewer..."
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

          <button 
            type="submit"
            disabled={submitting}
            className="w-full bg-white text-black hover:bg-gray-200 disabled:opacity-50 px-6 py-3.5 rounded-full font-medium transition-colors flex items-center justify-center gap-2 mt-2"
          >
            {submitting ? "Creating..." : "Create Agent"}
          </button>
        </form>
      </div>
    </div>
  );
}
