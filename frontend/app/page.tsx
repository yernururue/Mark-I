"use client";

import Image from "next/image";
import Header from "@/components/Header";
import { useState } from "react";
import LoginModal from "@/components/LoginModal";
import { Bot } from "lucide-react";

export default function Home() {
  const [isLoginOpen, setIsLoginOpen] = useState(false);
  return (
    <div className="relative flex flex-col items-center w-screen h-screen bg-black overflow-hidden font-sans">
      <Header />
      
      {/* Texture Grain Overlay */}
      <div className="pointer-events-none fixed inset-0 z-10 h-full w-full opacity-[0.15] mix-blend-plus-lighter">
        <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
          <filter id="noiseFilter">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="3" stitchTiles="stitch" />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width="100%" height="100%" filter="url(#noiseFilter)" />
        </svg>
      </div>

      {/* Scatter Dots Shader */}
      <div className="pointer-events-none fixed inset-0 z-10 h-full w-full opacity-[0.25] mix-blend-screen">
        <svg className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
          <filter id="scatterFilter">
            <feTurbulence type="fractalNoise" baseFrequency="1.5" numOctaves="2" stitchTiles="stitch" />
            <feColorMatrix type="matrix" values="0 0 0 0 1, 0 0 0 0 1, 0 0 0 0 1, 0 0 0 80 -55" />
          </filter>
          <rect width="100%" height="100%" filter="url(#scatterFilter)" />
        </svg>
      </div>

      <div className="absolute inset-0 z-0">
        <Image
          src="/background/city.png"
          alt="Background"
          fill
          priority
          className="object-cover"
        />
        {/* Vignette Overlay */}
        <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(ellipse_at_center,transparent_0%,rgba(0,0,0,0.7)_100%)]"></div>
      </div>
      <main className="absolute top-[30%] z-10 w-full max-w-4xl px-6 flex flex-col items-center gap-5 text-center">
        <h1 
          className="text-4xl md:text-6xl font-medium tracking-tight text-white drop-shadow-md leading-tight flex items-center justify-center gap-3 md:gap-4 flex-wrap font-sans"
        >
          <span>Meet</span>
          <span className="flex items-center gap-3 md:gap-4">
            <span className="font-serif italic">Mark-I</span>
            <span>Bot</span>
          </span>
        </h1>
        <p 
          className="text-base md:text-xl text-white/70 max-w-[700px] leading-relaxed font-sans font-light tracking-wide mt-1"
        >
          AI teammates you can give real work to. Bots can sign in to your tools, use them just like you do, and come back with finished work.
        </p>
        <div className="flex flex-col sm:flex-row items-center justify-center gap-3 mt-4">
          <button 
            onClick={() => setIsLoginOpen(true)}
            className="bg-white hover:bg-gray-100 text-black px-7 py-3 text-base font-medium rounded-full transition-colors flex items-center gap-2 w-full sm:w-auto justify-center"
          >
            Get Started
          </button>
          <a 
            href="#contact"
            className="bg-[#1C1C1C] hover:bg-[#2A2A2A] text-white/90 hover:text-white px-7 py-3 text-base font-medium rounded-full transition-colors w-full sm:w-auto text-center"
          >
            Contact sales
          </a>
        </div>
      </main>
      
      <LoginModal isOpen={isLoginOpen} onClose={() => setIsLoginOpen(false)} />
    </div>
  );
}
