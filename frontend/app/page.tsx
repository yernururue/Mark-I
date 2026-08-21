import Image from "next/image";
import Header from "@/components/Header";

export default function Home() {
  return (
    <div className="relative flex flex-col items-center w-screen h-screen bg-black overflow-hidden font-sans">
      <Header />
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
