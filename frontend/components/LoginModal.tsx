"use client";

import { useState } from "react";

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export default function LoginModal({ isOpen, onClose }: LoginModalProps) {
  if (!isOpen) return null;

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
          <h2 className="text-3xl font-serif italic text-white tracking-wide mb-2">Log in</h2>
          <p className="text-white/50 text-sm">Welcome back to Mark-I</p>
        </div>
        
        <form className="flex flex-col gap-5">
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans">Email</label>
            <input 
              type="email" 
              className="w-full bg-white/5 border border-white/10 text-white px-4 py-3 focus:outline-none focus:border-[#f05638]/50 transition-colors"
              placeholder="name@company.com"
            />
          </div>
          <div>
            <label className="block text-sm text-white/70 mb-2 font-sans flex justify-between">
              Password
              <a href="#" className="text-xs text-white/40 hover:text-white transition-colors">Forgot?</a>
            </label>
            <input 
              type="password" 
              className="w-full bg-white/5 border border-white/10 text-white px-4 py-3 focus:outline-none focus:border-[#f05638]/50 transition-colors"
              placeholder="••••••••"
            />
          </div>
          
          <button 
            type="submit"
            className="w-full bg-[#f05638] hover:bg-[#d94a30] text-white px-5 py-3 mt-4 text-sm font-serif font-bold transition-colors shadow-lg flex items-center justify-center gap-2"
          >
            Log in <span>&rarr;</span>
          </button>
        </form>

        <p className="text-white/50 text-sm text-center mt-8">
          Don't have an account? <a href="#" className="text-white hover:text-[#f05638] transition-colors">Sign up</a>
        </p>
      </div>
    </div>
  );
}
