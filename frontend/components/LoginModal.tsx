"use client";

import { useState, useEffect } from "react";
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
  initialIsSignUp?: boolean;
}

export default function LoginModal({ isOpen, onClose, initialIsSignUp = false }: LoginModalProps) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [repeatPassword, setRepeatPassword] = useState("");
  const [isSignUp, setIsSignUp] = useState(initialIsSignUp);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  // Reset isSignUp when modal opens with a new initial mode
  useEffect(() => {
    setIsSignUp(initialIsSignUp);
  }, [isOpen, initialIsSignUp]);

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
        className="bg-[#1C1C1C] border border-white/10 w-full max-w-md p-8 relative shadow-2xl rounded-3xl"
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
        
        <div className="text-center mb-8 mt-2">
          <h2 className="text-3xl font-sans font-medium text-white tracking-tight mb-2">
            {isSignUp ? "Sign up" : "Log in"}
          </h2>
          <p className="text-white/50 text-sm font-sans">Welcome to Mark-I</p>
        </div>
        
        <form className="flex flex-col gap-4" onSubmit={handleEmailAuth}>
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans font-medium">Email</label>
            <input 
              type="email" 
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl text-white px-4 py-3.5 focus:outline-none focus:border-white/30 transition-colors"
              placeholder="name@company.com"
              required
            />
          </div>
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans font-medium flex justify-between">
              Password
              {!isSignUp && <a href="#" className="text-xs text-white/40 hover:text-white transition-colors">Forgot?</a>}
            </label>
            <input 
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-white/5 border border-white/10 rounded-xl text-white px-4 py-3.5 focus:outline-none focus:border-white/30 transition-colors"
              placeholder="••••••••"
              required
            />
          </div>

          {isSignUp && (
            <div>
              <label className="block text-sm text-white/70 mb-2 font-sans font-medium">
                Repeat Password
              </label>
              <input 
                type="password"
                value={repeatPassword}
                onChange={(e) => setRepeatPassword(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl text-white px-4 py-3.5 focus:outline-none focus:border-white/30 transition-colors"
                placeholder="••••••••"
                required
              />
            </div>
          )}
          
          {error && <p className="text-red-500 text-sm">{error}</p>}

          <button 
            type="submit"
            disabled={loading}
            className="w-full bg-white hover:bg-gray-100 disabled:opacity-50 text-black rounded-full px-5 py-3.5 mt-2 text-[15px] font-medium transition-colors shadow-lg flex items-center justify-center gap-2"
          >
            {isSignUp ? "Sign up" : "Log in"}
          </button>
        </form>

        <div className="mt-6 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-white/10"></div>
            <span className="text-white/40 text-xs font-medium">OR</span>
            <div className="flex-1 h-px bg-white/10"></div>
          </div>
          
          <button 
            onClick={handleGoogleSignIn}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-white px-5 py-3.5 text-[15px] font-sans font-medium transition-colors flex items-center justify-center gap-2"
          >
            Continue with Google
          </button>
          
          <button 
            onClick={handleGithubSignIn}
            className="w-full bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-white px-5 py-3.5 text-[15px] font-sans font-medium transition-colors flex items-center justify-center gap-2"
          >
            Continue with GitHub
          </button>
        </div>

        <p className="text-white/50 text-sm text-center mt-8 font-sans">
          {isSignUp ? "Already have an account?" : "Don't have an account?"}{" "}
          <button 
            onClick={() => { setIsSignUp(!isSignUp); setError(null); }} 
            className="text-white hover:text-gray-300 font-medium transition-colors underline underline-offset-4"
          >
            {isSignUp ? "Log in" : "Sign up"}
          </button>
        </p>
      </div>
    </div>
  );
}
