"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Header from "@/components/Header";
import { useDashboardData } from "@/hooks/useDashboardData";
import SkillRadar from "@/components/dashboard/SkillRadar";
import ObservationFeed from "@/components/dashboard/ObservationFeed";
import DecisionLog from "@/components/dashboard/DecisionLog";
import { MessageCircle } from "lucide-react";
import Link from "next/link";

export default function Dashboard() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  
  const { profile, observations, decisions, loading: dataLoading } = useDashboardData(user?.uid);

  useEffect(() => {
    if (!authLoading && !user) {
      router.push("/");
    }
  }, [user, authLoading, router]);

  if (authLoading || !user || dataLoading) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <p className="text-white/50 text-sm font-sans animate-pulse">Loading dashboard...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <Header />
      
      <main className="pt-28 pb-12 px-6 lg:px-8 max-w-[1400px] mx-auto h-screen flex flex-col">
        
        {/* Top Header Section */}
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8 shrink-0">
          <div>
            <h1 className="text-3xl font-sans font-medium tracking-tight mb-2">
              Welcome back, {user.displayName || "Developer"}
            </h1>
            {profile?.goal ? (
              <p className="text-white/60 text-sm font-sans flex items-center gap-2">
                <span className="text-[#f05638] uppercase text-xs font-mono tracking-wider">Goal:</span> 
                {profile.goal}
              </p>
            ) : (
              <p className="text-white/50 text-sm font-sans">
                Set your learning goal in <Link href="/settings" className="underline hover:text-white">Settings</Link>.
              </p>
            )}
          </div>
          
          <div className="flex items-center gap-4">
            <div className="px-4 py-2 border border-white/10 bg-white/5 rounded-full text-xs font-mono text-white/60">
              Intensity: <span className="text-white capitalize">{profile?.intensity || "Normal"}</span>
            </div>
            
            <Link 
              href="/chat"
              className="flex items-center gap-2 px-5 py-2.5 bg-[#f05638] hover:bg-[#d94a30] text-white rounded-full text-sm font-sans font-medium transition-colors"
            >
              <MessageCircle className="w-4 h-4" />
              Chat with Agent
            </Link>
          </div>
        </div>
        
        {/* Dashboard Grid */}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-6">
          
          {/* Left Column: Skills (4 cols) */}
          <div className="lg:col-span-4 flex flex-col gap-6">
            <div className="flex-1 bg-white/[0.02] border border-white/10 rounded-xl p-6 relative overflow-hidden">
              <div className="absolute top-0 right-0 w-32 h-32 bg-[#f05638]/5 blur-3xl rounded-full" />
              <SkillRadar skills={profile?.skills} />
            </div>
          </div>
          
          {/* Middle Column: Activity Feed (4 cols) */}
          <div className="lg:col-span-5 bg-white/[0.02] border border-white/10 rounded-xl p-6">
            <ObservationFeed observations={observations} />
          </div>
          
          {/* Right Column: Decision Engine (4 cols) */}
          <div className="lg:col-span-3 bg-white/[0.02] border border-white/10 rounded-xl p-6">
            <DecisionLog decisions={decisions} />
          </div>
          
        </div>
        
      </main>
    </div>
  );
}
