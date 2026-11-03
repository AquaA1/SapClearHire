import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, ShieldCheck, User, ExternalLink, Sparkles } from 'lucide-react';

export const LandingPage: React.FC = () => {

  return (
    <div className="min-h-screen h-screen w-screen overflow-hidden bg-canvas text-ink flex flex-col justify-between p-3 sm:p-5 select-none relative font-sans">
      
      {/* ========================================================= */}
      {/* LARGE ROUNDED HERO CONTAINER (PRIMARY REFERENCE MATCH)    */}
      {/* ========================================================= */}
      <div className="relative w-full h-[calc(100vh-68px)] max-w-[1560px] mx-auto bg-surface border border-subtle rounded-[36px] sm:rounded-[44px] overflow-hidden flex flex-col justify-between p-6 sm:p-10 shadow-card">
        
        {/* ========================================================= */}
        {/* ANIMATED FLUID LIGHT FIELD LAYERS                         */}
        {/* ========================================================= */}
        {/* Fluid Light Orb 1 (Top-right ethereal drift) */}
        <div 
          className="absolute -top-24 -right-24 w-[720px] h-[720px] rounded-full bg-gradient-to-br from-accent/10 via-teal-100/30 to-transparent blur-[140px] pointer-events-none animate-fluid-light-1" 
        />
        
        {/* Fluid Light Orb 2 (Center-left fluid drift) */}
        <div 
          className="absolute -bottom-20 -left-20 w-[640px] h-[640px] rounded-full bg-gradient-to-tr from-accent/8 via-sky-100/25 to-transparent blur-[130px] pointer-events-none animate-fluid-light-2" 
        />
        
        {/* Central soft atmospheric glow */}
        <div 
          className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[850px] h-[500px] rounded-full bg-accent/[0.03] blur-[150px] pointer-events-none" 
        />

        {/* Vertical light streaks matching reference bottom center */}
        <div className="absolute bottom-12 left-1/2 -translate-x-1/2 flex items-end gap-3 pointer-events-none opacity-40">
          <div className="w-[1px] h-20 bg-gradient-to-t from-accent/40 to-transparent animate-beam-pulse" style={{ animationDelay: '0s' }} />
          <div className="w-[1px] h-32 bg-gradient-to-t from-accent/40 to-transparent animate-beam-pulse" style={{ animationDelay: '1.2s' }} />
          <div className="w-[1px] h-24 bg-gradient-to-t from-accent/40 to-transparent animate-beam-pulse" style={{ animationDelay: '2.4s' }} />
          <div className="w-[1px] h-16 bg-gradient-to-t from-accent/40 to-transparent animate-beam-pulse" style={{ animationDelay: '0.8s' }} />
        </div>

        {/* ========================================================= */}
        {/* TOP FLOATING NAVIGATION                                   */}
        {/* ========================================================= */}
        <header className="relative z-20 flex items-center justify-between w-full">
          {/* Logo (Top-Left circular mark matching reference) */}
          <Link to="/" className="flex items-center gap-3 group">
            <div className="w-10 h-10 rounded-full bg-accent flex items-center justify-center text-canvas font-black text-sm shadow-sm group-hover:scale-105 transition-transform">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none" className="text-canvas">
                <path
                  d="M12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2Z"
                  stroke="currentColor"
                  strokeWidth="3"
                />
                <circle cx="12" cy="12" r="4" fill="currentColor" />
              </svg>
            </div>
            <span className="font-bold text-ink text-base tracking-tight hidden sm:inline">
              ClearHire
            </span>
          </Link>

          {/* Centered Translucent Navigation Pill */}
          <nav className="hidden md:flex items-center gap-8 bg-elevated/70 backdrop-blur-xl border border-subtle rounded-full px-7 py-2.5 shadow-xs">
            <Link to="/candidate/jobs" className="text-sm font-semibold text-ink-secondary hover:text-ink transition-colors">
              Open Positions
            </Link>
            <Link to="/candidate/dashboard" className="text-sm font-semibold text-ink-secondary hover:text-ink transition-colors">
              Candidate Portal
            </Link>
            <Link to="/employer/dashboard" className="text-sm font-semibold text-ink-secondary hover:text-ink transition-colors">
              Employer Console
            </Link>
            
            <div className="h-4 w-[1px] bg-subtle" />

            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-surface border border-subtle text-ink text-xs sm:text-sm font-bold shadow-xs">
              <ShieldCheck className="w-4 h-4 text-accent" />
              <span>Transparency ↗</span>
            </div>
          </nav>

          {/* Top-Right Account Action matching reference */}
          <div className="flex items-center gap-4">
            <Link
              to="/register"
              className="flex items-center gap-2 text-sm font-semibold text-ink-secondary hover:text-ink transition-colors"
            >
              <User className="w-4 h-4" />
              <span>Create Account</span>
            </Link>
          </div>
        </header>

        {/* ========================================================= */}
        {/* DECORATIVE CONNECTED NODES (MATCHING REFERENCE COMPOSITION) */}
        {/* ========================================================= */}
        {/* Left Node: Criteria Grounding */}
        <div className="absolute top-1/3 left-10 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-85">
          <div className="w-8 h-8 rounded-full border border-subtle bg-elevated text-accent flex items-center justify-center text-sm font-bold shadow-xs">
            ▲
          </div>
          <div>
            <span className="text-sm font-bold text-ink block">• Criteria Grounding</span>
            <span className="text-xs font-mono text-muted">20.945 coordinates</span>
          </div>
        </div>

        {/* Left Bottom Node: OCR Extractor */}
        <div className="absolute bottom-1/3 left-12 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-85">
          <div className="w-8 h-8 rounded-full border border-subtle bg-elevated text-accent flex items-center justify-center text-sm font-bold shadow-xs">
            ❖
          </div>
          <div>
            <span className="text-sm font-bold text-ink block">• Verbatim Citation</span>
            <span className="text-xs font-mono text-muted">19.346 parsed</span>
          </div>
        </div>

        {/* Right Top Node: Human Triage */}
        <div className="absolute top-1/3 right-10 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-85">
          <div className="text-right">
            <span className="text-sm font-bold text-ink block">• Human Oversight</span>
            <span className="text-xs font-mono text-muted">2.945 verified</span>
          </div>
          <div className="w-8 h-8 rounded-full border border-subtle bg-elevated text-accent flex items-center justify-center text-sm font-bold shadow-xs">
            ✦
          </div>
        </div>

        {/* Right Bottom Node: Cryptographic Ledger */}
        <div className="absolute bottom-1/3 right-12 hidden xl:flex items-center gap-3 z-10 pointer-events-none opacity-85">
          <div className="text-right">
            <span className="text-sm font-bold text-ink block">• SHA-256 Chain</span>
            <span className="text-xs font-mono text-muted">440 blocks sealed</span>
          </div>
          <div className="w-8 h-8 rounded-full border border-subtle bg-elevated text-accent flex items-center justify-center text-sm font-bold shadow-xs">
            ⬡
          </div>
        </div>

        {/* ========================================================= */}
        {/* CENTER HERO SECTION                                       */}
        {/* ========================================================= */}
        <div className="relative z-20 my-auto text-center max-w-3xl mx-auto space-y-7">
          {/* Subtle Pill Sparkle Badge matching reference */}
          <div className="inline-flex items-center gap-2 px-5 py-2 rounded-full bg-accent-dim border border-accent/25 text-sm text-accent backdrop-blur-md shadow-xs font-semibold">
            <Sparkles className="w-4 h-4 text-accent" />
            <span>Unlock Your Hiring Evidence Spark! →</span>
          </div>

          {/* Hero Headline from User Prompt */}
          <h1 className="text-5xl sm:text-6xl md:text-7xl font-extrabold tracking-tight text-ink leading-[1.08]">
            See the Evidence.<br />
            Recognize the Potential.
          </h1>

          {/* Supporting Text from User Prompt */}
          <p className="text-base sm:text-lg text-ink-secondary max-w-xl mx-auto font-normal leading-relaxed">
            Transparent hiring starts with understanding the evidence behind every candidate. Zero black-box filters, zero fabricated scores.
          </p>

          {/* Two Prominent Action Buttons matching reference */}
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-3">
            <Link
              to="/login"
              className="w-full sm:w-auto px-9 py-4 bg-accent hover:bg-accent-secondary text-canvas font-bold text-sm sm:text-base rounded-full shadow-md hover:shadow-lg transition-all flex items-center justify-center gap-2.5 group cursor-pointer"
            >
              <span>Login</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </Link>

            <Link
              to="/register"
              className="w-full sm:w-auto px-8 py-4 bg-elevated hover:bg-surface text-ink font-bold text-sm sm:text-base rounded-full border border-subtle shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer"
            >
              <span>Create Account</span>
            </Link>
          </div>
        </div>

        {/* ========================================================= */}
        {/* BOTTOM METADATA BAR INSIDE HERO                           */}
        {/* ========================================================= */}
        <div className="relative z-20 flex items-center justify-between text-xs text-muted pt-4">
          <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-elevated border border-subtle text-[11px] font-mono text-ink-secondary">
            <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
            <span>01/03 • Evidence First Architecture</span>
          </div>

          <div className="text-right">
            <span className="text-[11px] font-mono text-muted block">ClearHire Protocol</span>
            <div className="flex gap-1 justify-end mt-1">
              <span className="w-6 h-1 rounded-full bg-accent" />
              <span className="w-2 h-1 rounded-full bg-subtle" />
              <span className="w-2 h-1 rounded-full bg-subtle" />
            </div>
          </div>
        </div>

      </div>

      {/* ========================================================= */}
      {/* MONOCHROME PARTNER / ECOSYSTEM LOGOS (VERY BOTTOM)        */}
      {/* ========================================================= */}
      <footer className="h-12 max-w-[1560px] mx-auto w-full px-8 flex items-center justify-between text-xs text-muted font-mono overflow-hidden">
        <span className="hidden sm:inline text-muted font-medium">Enterprise Verified</span>
        <div className="flex items-center gap-8 sm:gap-12 mx-auto sm:mx-0 opacity-70 hover:opacity-100 transition-opacity text-ink-secondary">
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
