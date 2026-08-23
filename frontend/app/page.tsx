import Image from "next/image";
import Header from "@/components/Header";

export default function Home() {
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
          src="/background/image1.png"
          alt="Background"
          fill
          priority
          className="object-contain"
        />
      </div>
      <main className="absolute top-[25%] z-10 w-full max-w-5xl px-6 flex flex-col items-center gap-8 text-center">
        <h1 className="text-3xl md:text-4xl font-light tracking-wide text-white/90 drop-shadow-md leading-tight">
          AI agent that keeps everything in line
        </h1>
        <button className="bg-[#f05638] hover:bg-[#d94a30] text-white px-8 py-3 text-sm font-serif font-bold shadow-lg transition-colors flex items-center gap-1.5">
          Get started <span>&rarr;</span>
        </button>
      </main>
    </div>
  );
}
