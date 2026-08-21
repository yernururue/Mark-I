import Link from "next/link";

export default function Header() {
  return (
    <header className="fixed top-0 left-0 right-0 z-50 px-8 py-6 w-full">
      <div className="w-full mx-auto flex items-center justify-between">
        
        {/* Left Navigation Links */}
        <nav className="hidden md:flex items-center gap-8 flex-1">
          <Link href="#product" className="text-white/80 hover:text-white text-sm transition-colors flex items-center gap-1">
            Product
            <svg className="w-3 h-3 opacity-70" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
            </svg>
          </Link>
          <Link href="#agents" className="text-white/80 hover:text-white text-sm transition-colors">
            Agents
          </Link>
          <Link href="#enterprise" className="text-white/80 hover:text-white text-sm transition-colors">
            Enterprise
          </Link>
          <Link href="#pricing" className="text-white/80 hover:text-white text-sm transition-colors">
            Pricing
          </Link>
        </nav>

        {/* Center Logo */}
        <div className="flex items-center justify-center flex-1">
          <Link href="/" className="text-white text-3xl font-serif italic tracking-wide">
            Mark-I
          </Link>
        </div>

        {/* Right Links & Button */}
        <div className="hidden md:flex items-center justify-end gap-8 flex-1">
          <Link href="#docs" className="text-white/80 hover:text-white text-sm transition-colors">
            Docs
          </Link>
          <button className="bg-[#f05638] hover:bg-[#d94a30] text-white px-5 py-2 text-sm font-serif font-bold transition-colors">
            Sign up
          </button>
        </div>
      </div>
    </header>
  );
}
