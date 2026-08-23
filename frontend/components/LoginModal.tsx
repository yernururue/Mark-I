"use client";

import { useState } from "react";
import { 
  signInWithPopup, 
  signInWithEmailAndPassword, 
  createUserWithEmailAndPassword 
} from 'firebase/auth';
import { auth, googleProvider, githubProvider } from '@/lib/firebase';
import { useRouter } from 'next/navigation';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  if (!isOpen) return null;

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (isSignUp) {
        if (password !== repeatPassword) {
          setError("Passwords do not match");
          setLoading(false);
          return;
        }
        await createUserWithEmailAndPassword(auth, email, password);
      } else {
        await signInWithEmailAndPassword(auth, email, password);
      }
      onClose();
      router.push(isSignUp ? '/onboarding' : '/dashboard');
    } catch (err: any) {
      setError(err.message || "Failed to authenticate");
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignIn = async () => {
    try {
      const result = await signInWithPopup(auth, googleProvider);
      onClose();
      // Check if this is a new user by comparing creation and last sign in times
      const isNewUser = result.user.metadata.creationTime === result.user.metadata.lastSignInTime;
      router.push(isNewUser ? '/onboarding' : '/dashboard');
    } catch (err: any) {
      setError(err.message || "Google sign-in failed");
    }
  };

  const handleGithubSignIn = async () => {
    try {
      const result = await signInWithPopup(auth, githubProvider);
      onClose();
      // Check if this is a new user
      const isNewUser = result.user.metadata.creationTime === result.user.metadata.lastSignInTime;
      router.push(isNewUser ? '/onboarding' : '/dashboard');
    } catch (err: any) {
      setError(err.message || "GitHub sign-in failed");
    }
  };

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div 
        className="bg-[#0a0a0a] border border-white/10 w-full max-w-md p-8 relative shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-white/40 hover:text-white transition-colors"
        >
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        
        <div className="text-center mb-8">
          <h2 className="text-3xl font-serif italic text-white tracking-wide mb-2">
            {isSignUp ? "Sign up" : "Log in"}
          </h2>
          <p className="text-white/50 text-sm">Welcome to Mark-I</p>
        </div>
        
        <form className="flex flex-col gap-5" onSubmit={handleEmailAuth}>
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-white/5 border border-white/10 text-white px-4 py-3 focus:outline-none focus:border-[#f05638]/50 transition-colors"
              placeholder="name@company.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans flex justify-between">
              Password
              {!isSignUp && <a href="#" className="text-xs text-white/40 hover:text-white transition-colors">Forgot?</a>}
            </label>
            <input 
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-white/5 border border-white/10 text-white px-4 py-3 focus:outline-none focus:border-[#f05638]/50 transition-colors"
              placeholder="••••••••"
              required
            />
          </div>

          {isSignUp && (
            <div>
              <label className="block text-sm text-white/70 mb-2 font-sans">
                Repeat Password
              </label>
              <input 
                type="password"
                value={repeatPassword}
                onChange={(e) => setRepeatPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 text-white px-4 py-3 focus:outline-none focus:border-[#f05638]/50 transition-colors"
                placeholder="••••••••"
                required
              />
            </div>
          )}
          
          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-[#f05638] hover:bg-[#d94a30] disabled:opacity-50 text-white px-5 py-3 mt-4 text-sm font-serif font-bold transition-colors shadow-lg flex items-center justify-center gap-2"
          >
            {isSignUp ? "Sign up" : "Log in"} <span>&rarr;</span>
          </button>
        </form>

        <div className="mt-6 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="text-white/40 text-xs">OR</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>
          
          <button 
            onClick={handleGoogleSignIn}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 text-white px-5 py-3 text-sm font-sans transition-colors flex items-center justify-center gap-2"
          >
            Continue with Google
          </button>
          
          <button 
            onClick={handleGithubSignIn}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 text-white px-5 py-3 text-sm font-sans transition-colors flex items-center justify-center gap-2"
          >
            Continue with GitHub
          </button>
        </div>

        <p className="text-white/50 text-sm text-center mt-8">
          {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
          <button 
            onClick={() => { setIsSignUp(!isSignUp); setError(null); }} 
            className="text-white hover:text-[#f05638] transition-colors"
          >
            {isSignUp ? "Log in" : "Sign up"}
          </button>
        </p>
      </div>
    </div>
  );
}
