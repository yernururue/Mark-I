"use client";

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { fetchApi } from "@/lib/api";

const INTENSITIES = [
  { id: "chill", label: "Chill", desc: "Weekly check-ins, occasional opportunities." },
  { id: "normal", label: "Normal", desc: "Balanced updates on your coding progress." },
  { id: "brutal", label: "Brutal", desc: "Constant feedback, strict tracking, no slacking." }
];

export default function Onboarding() {
  const { user, loading } = useAuth();
  const router = useRouter();
  
  const [goal, setGoal] = useState("");
  const [intensity, setIntensity] = useState("normal");
  const [language, setLanguage] = useState("English");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) {
      router.push("/");
    }
  }, [user, loading, router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    
    try {
      // POST to backend API (or fallback for demo purposes if backend isn't ready)
      await fetchApi("/users/profile", {
        method: "POST",
        body: JSON.stringify({
          goal,
          intensity,
          language
        })
      }).catch(err => {
        console.warn("Backend not ready, skipping API call for demo...", err);
      });
      
      // Navigate to dashboard upon completion
      router.push("/dashboard");
    } catch (err: any) {
      setError(err.message || "Failed to save profile");
    } finally {
      setSubmitting(false);
    }
  };

  if (loading || !user) {
    return <div className="min-h-screen bg-[#050505]"></div>;
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white flex flex-col items-center justify-center p-8">
      <div className="max-w-xl w-full">
        <h1 className="text-4xl font-serif italic mb-2">Welcome to Mark-I</h1>
        <p className="text-white/50 mb-10 font-sans">Let's set up your personal AI mentor.</p>
        
        <form onSubmit={handleSubmit} className="space-y-8">
          {/* Goal Section */}
          <div className="space-y-3">
            <label className="block text-lg font-sans font-medium text-white">
              What is your primary learning goal?
            </label>
            <p className="text-white/40 text-sm">Be specific. e.g., "Get a junior frontend job in 3 months" or "Master Data Structures in Python"</p>
            <input 
              type="text"
              value={goal}
              onChange={(e) => setGoal(e.target.value)}
              required
              className="w-full bg-white/5 border border-white/10 px-4 py-3 text-white focus:outline-none focus:border-[#f05638]/50 transition-colors"
              placeholder="Your goal..."
            />
          </div>

          {/* Intensity Section */}
          <div className="space-y-3">
            <label className="block text-lg font-sans font-medium text-white">
              Mentorship Intensity
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {INTENSITIES.map(opt => (
                <div 
                  key={opt.id}
                  onClick={() => setIntensity(opt.id)}
                  className={`cursor-pointer border p-4 transition-colors ${
                    intensity === opt.id 
                      ? "border-[#f05638] bg-[#f05638]/10" 
                      : "border-white/10 bg-white/5 hover:border-white/30"
                  }`}
                >
                  <h3 className="font-serif italic text-lg mb-1">{opt.label}</h3>
                  <p className="text-white/50 text-xs">{opt.desc}</p>
                </div>
              ))}
            </div>
          </div>
          
          {/* Language Section */}
          <div className="space-y-3">
            <label className="block text-lg font-sans font-medium text-white">
              Agent Language
            </label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full bg-[#0a0a0a] border border-white/10 px-4 py-3 text-white focus:outline-none focus:border-[#f05638]/50 transition-colors"
            >
              <option value="English">English</option>
              <option value="Russian">Russian</option>
              <option value="Spanish">Spanish</option>
            </select>
          </div>

          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button 
            type="submit"
            disabled={submitting}
            className="w-full bg-[#f05638] hover:bg-[#d94a30] disabled:opacity-50 text-white px-5 py-4 text-sm font-serif font-bold transition-colors shadow-lg flex items-center justify-center gap-2 mt-4"
          >
            {submitting ? "Saving..." : "Start Journey"} <span>&rarr;</span>
          </button>
        </form>
      </div>
    </div>
  );
}
