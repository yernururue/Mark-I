"use client";

import Link from "next/link";
import { useState } from "react";
import LoginModal from "./LoginModal";
import { useAuth } from "@/contexts/AuthContext";

export default function Header() {
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  const [isSignUpMode, setIsSignUpMode] = useState(false);
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const { user, signOut } = useAuth();

  return (
    <>
      <header className="fixed top-0 left-0 right-0 z-50 px-8 py-6 w-full">
        <div className="w-full mx-auto flex items-center justify-between">
          
          <div className="flex items-center gap-12">
            {/* Logo */}
            <Link href="/" className="text-white text-3xl font-serif italic tracking-wide">
              Mark-I
            </Link>

            {/* Navigation Links */}
            <nav className="hidden md:flex items-center gap-6">
              <Link href="#products" className="text-white/80 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                Products
                <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Link>
              <Link href="#solutions" className="text-white/80 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                Solutions
                <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Link>
              <Link href="#developer" className="text-white/80 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                Developer
                <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Link>
              <Link href="#company" className="text-white/80 hover:text-white text-sm transition-colors flex items-center gap-1.5">
                Company
                <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </Link>
              <Link href="#pricing" className="text-white/80 hover:text-white text-sm transition-colors">
                Pricing
              </Link>
              <Link href="#news" className="text-white/80 hover:text-white text-sm transition-colors">
                News
              </Link>
            </nav>
          </div>

          {/* Right Links & Button */}
          <div className="hidden md:flex items-center justify-end gap-4">
            
            {user ? (
              <div className="flex items-center gap-4">
                <span className="text-white/60 text-sm">
                  {user.displayName || user.email}
                </span>
                <Link 
                  href="/dashboard"
                  className="bg-white/10 hover:bg-white/20 text-white px-5 py-2.5 rounded-full text-sm font-sans transition-colors"
                >
                  Dashboard
                </Link>
                <button 
                  onClick={signOut}
                  className="text-white/60 hover:text-white text-sm transition-colors"
                >
                  Sign Out
                </button>
              </div>
            ) : (
              <>
                <Link 
                  href="#contact" 
                  className="px-5 py-2.5 text-sm text-white/90 hover:text-white border border-white/20 hover:border-white/40 rounded-full transition-colors"
                >
                  Contact Sales
                </Link>
                <div className="relative flex items-center bg-white text-black rounded-full transition-colors hover:bg-gray-100">
                  <button 
                    onClick={() => { setIsSignUpMode(false); setIsLoginOpen(true); }}
                    className="px-4 py-2.5 pl-5 text-sm font-medium"
                  >
                    Log in
                  </button>
                  <div className="w-px h-5 bg-black/10"></div>
                  <button 
                    onClick={() => setIsDropdownOpen(!isDropdownOpen)}
                    className="px-3 py-2.5 rounded-r-full text-sm flex items-center justify-center"
                  >
                    <svg className={`w-3.5 h-3.5 transition-transform duration-200 ${isDropdownOpen ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {/* Dropdown */}
                  <div 
                    className={`absolute right-0 top-full mt-2 w-full bg-gray-100 text-black rounded-full overflow-hidden shadow-xl transition-all duration-300 origin-top ${
                      isDropdownOpen ? 'opacity-100 translate-y-0' : 'opacity-0 -translate-y-2 pointer-events-none'
                    }`}
                  >
                    <button 
                      onClick={() => {
                        setIsDropdownOpen(false);
                        setIsSignUpMode(true);
                        setIsLoginOpen(true);
                      }}
                      className="w-full text-center px-4 py-2.5 text-sm font-medium hover:bg-gray-200 transition-colors"
                    >
                      Sign up
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </header>
      
      <LoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} initialIsSignUp={isSignUpMode} />
    </>
  );
}
