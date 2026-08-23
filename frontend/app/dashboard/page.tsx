"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import Header from "@/components/Header";

export default function Dashboard() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  if (loading || !user) {
    return (
      <div className="min-h-screen bg-[#050505] flex items-center justify-center">
        <p className="text-white/50 text-sm font-sans">Loading...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white">
      <Header />
      
      <main className="pt-32 px-8 max-w-7xl mx-auto">
        <h1 className="text-4xl font-sans font-medium tracking-tight mb-8">
          Welcome back, {user.displayName || "Developer"}
        </h1>
        
        <div className="border border-white/10 p-12 bg-white/5 rounded-sm flex items-center justify-center min-h-[400px]">
          <p className="text-white/40 font-sans">
            Dashboard under construction...
          </p>
        </div>
      </main>
    </div>
  );
}
