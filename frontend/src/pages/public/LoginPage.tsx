import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, Check } from 'lucide-react';
import { InteractiveCharacters } from '../../components/auth/InteractiveCharacters';
import { useAuth } from '../../stores/authStore';
import { UserRole } from '../../contracts/enums';
import { Button } from '../../components/ui';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [email, setEmail] = useState('cody.fisher@example.com');
  const [password, setPassword] = useState('777G555A888');
  const [showPassword, setShowPassword] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);
  const [focusedField, setFocusedField] = useState<'email' | 'password' | null>(null);
  const [isTyping, setIsTyping] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isSuccess, setIsSuccess] = useState(false);
  const [selectedRole, setSelectedRole] = useState<UserRole>(UserRole.CANDIDATE);

  const handleRolePreset = (role: UserRole) => {
    setSelectedRole(role);
    if (role === UserRole.CANDIDATE) {
      setEmail('cody.fisher@example.com');
    } else if (role === UserRole.EMPLOYER_ADMIN) {
      setEmail('bagus.fikri@fikristudio.com');
    } else if (role === UserRole.REVIEWER) {
      setEmail('andri.herdiansyah@fikristudio.com');
    } else if (role === UserRole.SYSTEM_AUDITOR) {
      setEmail('kathryn.murphy@auditgov.org');
    }
  };

  const handleTyping = (setter: React.Dispatch<React.SetStateAction<string>>, val: string) => {
    setter(val);
    setIsTyping(true);
    const timeout = setTimeout(() => setIsTyping(false), 200);
    return () => clearTimeout(timeout);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      await login(email, selectedRole);
      setIsSuccess(true);

      setTimeout(() => {
        if (selectedRole === UserRole.CANDIDATE) {
          navigate('/candidate/dashboard');
        } else if (selectedRole === UserRole.EMPLOYER_ADMIN) {
          navigate('/employer/dashboard');
        } else if (selectedRole === UserRole.REVIEWER) {
          navigate('/reviewer/queue');
        } else if (selectedRole === UserRole.SYSTEM_AUDITOR) {
          navigate('/reviewer/queue');
        }
      }, 700);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-canvas flex items-center justify-center p-4 sm:p-6 md:p-10 select-none">
      {/* Outer Card */}
      <div className="w-full max-w-5xl bg-surface rounded-card overflow-hidden shadow-card grid grid-cols-1 lg:grid-cols-12 border border-subtle">
        
        {/* Left Panel: Interactive Illustration Area */}
        <div className="lg:col-span-6 p-8 sm:p-12 flex flex-col justify-between relative bg-elevated/40 border-b lg:border-b-0 lg:border-r border-subtle">
          {/* Top Logo */}
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-card bg-accent flex items-center justify-center font-bold text-canvas text-sm">
              CH
            </div>
            <span className="font-semibold text-ink tracking-tight text-lg">ClearHire</span>
            <span className="text-[10px] font-mono font-medium px-2 py-0.5 rounded-pill bg-accent-dim text-accent border border-accent/20 ml-1">
              Evidence Engine
            </span>
          </div>

          {/* Interactive Characters Rig (Preserved) */}
          <div className="my-auto py-6">
            <InteractiveCharacters
              focusedField={focusedField}
              isTyping={isTyping}
              showPassword={showPassword}
              isSuccess={isSuccess}
            />
          </div>

          {/* Bottom Headline */}
          <div className="text-left mt-2">
            <h2 className="text-lg sm:text-xl font-semibold text-ink tracking-tight leading-snug">
              Every qualification claim.<br />
              <span className="text-accent">Verifiably grounded.</span>
            </h2>
            <p className="text-muted text-xs mt-1 leading-relaxed font-medium">
              Factual candidate screening anchored directly to verbatim resume excerpts with human reviewer oversight.
            </p>
          </div>
        </div>

        {/* Right Panel: Login Form Container */}
        <div className="lg:col-span-6 bg-surface p-8 sm:p-12 flex flex-col justify-between">
          <div className="space-y-6">
            {/* Header */}
            <div>
              <h1 className="text-2xl sm:text-3xl font-semibold text-ink tracking-tight">
                Welcome back
              </h1>
              <p className="text-muted text-xs mt-1 font-medium">
                Please enter your credentials or select a demo role
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Email Field */}
              <div className="text-left space-y-1">
                <label className="block text-xs font-semibold text-muted">
                  Email Address
                </label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => handleTyping(setEmail, e.target.value)}
                  onFocus={() => setFocusedField('email')}
                  onBlur={() => setFocusedField(null)}
                  required
                  className="w-full text-xs py-2.5 px-3 bg-elevated border border-subtle rounded-sm text-ink font-medium focus:border-accent focus:outline-none placeholder:text-muted"
                  placeholder="name@example.com"
                />
              </div>

              {/* Password Field */}
              <div className="text-left space-y-1 relative">
                <label className="block text-xs font-semibold text-muted">
                  Password
                </label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    value={password}
                    onChange={(e) => handleTyping(setPassword, e.target.value)}
                    onFocus={() => setFocusedField('password')}
                    onBlur={() => setFocusedField(null)}
                    required
                    className="w-full text-xs py-2.5 px-3 bg-elevated border border-subtle rounded-sm text-ink font-medium focus:border-accent focus:outline-none placeholder:text-muted pr-10"
                    placeholder="••••••••••••"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-muted hover:text-ink p-1 transition-colors cursor-pointer"
                    title={showPassword ? 'Hide password' : 'Peek password'}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Remember Me */}
              <div className="flex items-center justify-between text-xs pt-1 font-medium">
                <label className="flex items-center gap-2 cursor-pointer text-muted">
                  <input
                    type="checkbox"
                    checked={rememberMe}
                    onChange={(e) => setRememberMe(e.target.checked)}
                    className="rounded-sm border-subtle bg-elevated text-accent focus:ring-0 w-3.5 h-3.5 accent-accent"
                  />
                  <span>Remember session</span>
                </label>
                <a href="#forgot" className="text-muted hover:text-ink transition-colors">
                  Forgot password?
                </a>
              </div>

              {/* Primary Login Button */}
              <Button
                type="submit"
                disabled={isLoading || isSuccess}
                isLoading={isLoading}
                variant="primary"
                size="md"
                className="w-full justify-center font-semibold mt-2"
              >
                {isSuccess ? (
                  <span className="flex items-center gap-2 text-canvas">
                    <Check className="w-4 h-4" /> Authenticated!
                  </span>
                ) : (
                  'Sign In'
                )}
              </Button>
            </form>

            {/* Demo Persona Quick Switch */}
            <div className="pt-4 border-t border-subtle">
              <span className="text-[10px] font-semibold text-muted uppercase tracking-wider block mb-2 text-center">
                Instant Demo Persona Select
              </span>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5">
                {[
                  { role: UserRole.CANDIDATE, label: 'Candidate' },
                  { role: UserRole.EMPLOYER_ADMIN, label: 'Employer' },
                  { role: UserRole.REVIEWER, label: 'Reviewer' },
                  { role: UserRole.SYSTEM_AUDITOR, label: 'Auditor' },
                ].map(({ role, label }) => (
                  <button
                    key={role}
                    type="button"
                    onClick={() => handleRolePreset(role)}
                    className={`py-1.5 px-2 rounded-pill text-[11px] font-semibold border transition-all text-center cursor-pointer ${
                      selectedRole === role
                        ? 'bg-accent text-canvas border-accent shadow-sm'
                        : 'bg-elevated text-muted border-subtle hover:text-ink'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Registration Link */}
          <div className="text-center pt-6 text-xs text-muted font-medium">
            Don't have an account?{' '}
            <Link to="/register" className="font-semibold text-accent hover:underline">
              Create an Account
            </Link>
          </div>
        </div>

      </div>
    </div>
  );
};
