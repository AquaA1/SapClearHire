import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, User, ExternalLink, Sparkles } from 'lucide-react';

export const LandingPage: React.FC = () => {

  return (
    <div className="min-h-screen h-screen w-screen overflow-hidden bg-[#080808] text-white flex flex-col justify-between p-3 sm:p-5 select-none relative font-sans">
      
      {/* ========================================================= */}
      {/* LARGE ROUNDED HERO CONTAINER (PRIMARY REFERENCE MATCH)    */}
      {/* ========================================================= */}
      <div className="relative w-full h-[calc(100vh-68px)] max-w-[1560px] mx-auto bg-[#070707] border border-white/10 rounded-[36px] sm:rounded-[44px] overflow-hidden flex flex-col justify-between p-6 sm:p-10 shadow-2xl">
        
        {/* ========================================================= */}
        {/* ANIMATED BLACK-AND-WHITE FLUID LIGHT FIELD LAYERS         */}
        {/* ========================================================= */}
        {/* Fluid Light Orb 1 (Top-right ethereal drift) */}
        <div 
          className="absolute -top-24 -right-24 w-[720px] h-[720px] rounded-full bg-gradient-to-br from-white/25 via-zinc-200/15 to-transparent blur-[140px] pointer-events-none animate-fluid-light-1" 
        />
        
        {/* Fluid Light Orb 2 (Center-left fluid drift) */}
        <div 
          className="absolute -bottom-20 -left-20 w-[640px] h-[640px] rounded-full bg-gradient-to-tr from-white/20 via-zinc-300/10 to-transparent blur-[130px] pointer-events-none animate-fluid-light-2" 
        />
        
        {/* Central soft atmospheric glow */}
        <div 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[850px] h-[500px] rounded-full bg-white/[0.04] blur-[150px] pointer-events-none" 
        />

        {/* Vertical light streaks matching reference bottom center */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-end gap-3 pointer-events-none opacity-40">
          <div className="w-[1px] h-20 bg-gradient-to-t from-white to-transparent animate-beam-pulse" style={{ animationDelay: '0s' }} />
          <div className="w-[1px] h-32 bg-gradient-to-t from-white to-transparent animate-beam-pulse" style={{ animationDelay: '1.2s' }} />
          <div className="w-[1px] h-24 bg-gradient-to-t from-white to-transparent animate-beam-pulse" style={{ animationDelay: '2.4s' }} />
          <div className="w-[1px] h-16 bg-gradient-to-t from-white to-transparent animate-beam-pulse" style={{ animationDelay: '0.8s' }} />
        </div>

        {/* ========================================================= */}
        {/* TOP FLOATING NAVIGATION                                   */}
        {/* ========================================================= */}
        <header className="relative z-20 flex items-center justify-between w-full">
          {/* Logo (Top-Left circular mark matching reference) */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-full bg-white flex items-center justify-center text-black font-black text-sm shadow-md group-hover:scale-105 transition-transform">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-black">
                <path
                  d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2Z"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <circle cx="12" cy="12" r="4" fill="currentColor" />
              </svg>
            </div>
            <span className="font-bold text-white text-base tracking-tight hidden sm:inline">
              ClearHire
            </span>
          </Link>

          {/* Centered Translucent Navigation Pill */}
          <nav className="hidden md:flex items-center gap-7 bg-white/[0.04] backdrop-blur-xl border border-white/10 rounded-full px-6 py-2 shadow-lg">
            <Link to="/benchmark" className="text-xs font-medium text-zinc-300 hover:text-white transition-colors">
              Evidence Engine
            </Link>
            <Link to="/auditor/chain" className="text-xs font-medium text-zinc-300 hover:text-white transition-colors">
              Audit Chain
            </Link>
            <Link to="/candidate/jobs" className="text-xs font-medium text-zinc-300 hover:text-white transition-colors">
              Openings
            </Link>
            <Link to="/benchmark" className="text-xs font-medium text-zinc-300 hover:text-white transition-colors">
              Benchmark
            </Link>
            
            <div className="h-3.5 w-[1px] bg-white/15" />

            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-white/10 text-white text-xs font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-zinc-300" />
              <span>Transparency ↗</span>
            </div>
          </nav>

          {/* Top-Right Account Action matching reference */}
          <div className="flex items-center gap-4">
            <Link
              to="/register"
              className="flex items-center gap-2 text-xs font-medium text-zinc-300 hover:text-white transition-colors"
            >
              <User className="w-3.5 h-3.5" />
              <span>Create Account</span>
            </Link>
          </div>
        </header>

        {/* ========================================================= */}
        {/* DECORATIVE CONNECTED NODES (MATCHING REFERENCE COMPOSITION) */}
        {/* ========================================================= */}
        {/* Left Node: Criteria Grounding */}
        <div className="absolute top-1/3 left-10 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-70">
          <div className="w-7 h-7 rounded-full border border-white/20 bg-white/5 flex items-center justify-center text-xs">
            ▲
          </div>
          <div>
            <span className="text-xs font-semibold text-white block">• Criteria Grounding</span>
            <span className="text-[10px] font-mono text-zinc-400">20.945 coordinates</span>
          </div>
        </div>

        {/* Left Bottom Node: OCR Extractor */}
        <div className="absolute bottom-1/3 left-12 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-70">
          <div className="w-7 h-7 rounded-full border border-white/20 bg-white/5 flex items-center justify-center text-xs">
            ❖
          </div>
          <div>
            <span className="text-xs font-semibold text-white block">• Verbatim Citation</span>
            <span className="text-[10px] font-mono text-zinc-400">19.346 parsed</span>
          </div>
        </div>

        {/* Right Top Node: Human Triage */}
        <div className="absolute top-1/3 right-10 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-70">
          <div className="text-right">
            <span className="text-xs font-semibold text-white block">• Human Oversight</span>
            <span className="text-[10px] font-mono text-zinc-400">2.945 verified</span>
          </div>
          <div className="w-7 h-7 rounded-full border border-white/20 bg-white/5 flex items-center justify-center text-xs">
            ✦
          </div>
        </div>

        {/* Right Bottom Node: Cryptographic Ledger */}
        <div className="absolute bottom-1/3 right-12 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-70">
          <div className="text-right">
            <span className="text-xs font-semibold text-white block">• SHA-256 Chain</span>
            <span className="text-[10px] font-mono text-zinc-400">440 blocks sealed</span>
          </div>
          <div className="w-7 h-7 rounded-full border border-white/20 bg-white/5 flex items-center justify-center text-xs">
            ⬡
          </div>
        </div>

        {/* ========================================================= */}
        {/* CENTER HERO SECTION                                       */}
        {/* ========================================================= */}
        <div className="relative z-20 my-auto text-center max-w-3xl mx-auto space-y-6">
          {/* Subtle Pill Sparkle Badge matching reference */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/[0.06] border border-white/15 text-xs text-zinc-200 backdrop-blur-md shadow-sm">
            <Sparkles className="w-3.5 h-3.5 text-white" />
            <span>Unlock Your Hiring Evidence Spark! →</span>
          </div>

          {/* Hero Headline from User Prompt */}
          <h1 className="text-4xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-white leading-[1.08]">
            See the Evidence.<br />
            Recognize the Potential.
          </h1>

          {/* Supporting Text from User Prompt */}
          <p className="text-sm sm:text-base text-zinc-300 max-w-xl mx-auto font-normal leading-relaxed">
            Transparent hiring starts with understanding the evidence behind every candidate. Zero black-box filters, zero fabricated scores.
          </p>

          {/* Two Prominent Action Buttons matching reference */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-3 pt-3">
            <Link
              to="/login"
              className="w-full sm:w-auto px-8 py-3.5 bg-white hover:bg-zinc-200 text-black font-semibold text-xs rounded-full shadow-lg hover:shadow-xl transition-all flex items-center justify-center gap-2 group"
            >
              <span>Login</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>

            <Link
              to="/register"
              className="w-full sm:w-auto px-7 py-3.5 bg-white/[0.06] hover:bg-white/[0.12] text-white font-semibold text-xs rounded-full border border-white/20 backdrop-blur-md transition-all flex items-center justify-center gap-2"
            >
              <span>Create Account</span>
            </Link>
          </div>
        </div>

        {/* ========================================================= */}
        {/* BOTTOM METADATA BAR INSIDE HERO                           */}
        {/* ========================================================= */}
        <div className="relative z-20 flex items-center justify-between text-xs text-zinc-400 pt-4">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/[0.04] border border-white/10 text-[11px] font-mono">
            <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
            <span>01/03 • Evidence First Architecture</span>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-mono text-zinc-400 block">ClearHire Protocol</span>
            <div className="flex gap-1 justify-end mt-1">
              <span className="w-6 h-1 rounded-full bg-white" />
              <span className="w-2 h-1 rounded-full bg-white/20" />
              <span className="w-2 h-1 rounded-full bg-white/20" />
            </div>
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* MONOCHROME PARTNER / ECOSYSTEM LOGOS (VERY BOTTOM)        */}
      {/* ========================================================= */}
      <footer className="h-12 max-w-[1560px] mx-auto w-full px-8 flex items-center justify-between text-xs text-zinc-500 font-mono overflow-hidden">
        <span className="hidden sm:inline text-zinc-600">Enterprise Verified</span>
        <div className="flex items-center gap-8 sm:gap-12 mx-auto sm:mx-0 opacity-60 hover:opacity-80 transition-opacity">
          <span>▲ SAP SuccessFactors</span>
          <span>✦ Workday</span>
          <span>⬡ Greenhouse</span>
          <span>◈ Apache Kafka</span>
          <span>● Kubernetes</span>
        </div>
      </footer>

    </div>
  );
};
