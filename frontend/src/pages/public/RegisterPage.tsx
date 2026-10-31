import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { ShieldCheck, ArrowRight, AlertCircle } from 'lucide-react';
import { useAuth } from '../../stores/authStore';
import { Button } from '../../components/ui';

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate();
  const { register } = useAuth();

  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setErrorMessage(null);

    try {
      await register(fullName, email, password);
      navigate('/candidate/dashboard');
    } catch (err: unknown) {
      const errObj = err as { message?: string };
      setErrorMessage(errObj.message || 'Registration failed. Please check your details and try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-canvas flex items-center justify-center p-4 sm:p-6 select-none">
      <div className="w-full max-w-md bg-surface rounded-card p-8 sm:p-10 shadow-card border border-subtle">
        <div className="text-center mb-8">
          <div className="inline-flex w-12 h-12 rounded-card bg-accent-dim text-accent border border-accent/30 items-center justify-center mb-4">
            <ShieldCheck className="w-6 h-6" />
          </div>
          <h1 className="text-2xl sm:text-3xl font-semibold text-ink tracking-tight">Create your account</h1>
          <p className="text-muted text-xs sm:text-sm mt-1 max-w-sm mx-auto font-medium">
            Join ClearHire as a candidate and get full visibility into how your resume evidence is screened.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Error Banner */}
          {errorMessage && (
            <div className="p-3 rounded-card bg-danger/10 border border-danger/30 text-danger text-xs font-medium flex items-start gap-2">
              <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
              <span className="leading-snug">{errorMessage}</span>
            </div>
          )}

          <div className="space-y-1">
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider">
              Full Name
            </label>
            <input
              type="text"
              required
              value={fullName}
              onChange={(e) => {
                setFullName(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder="e.g. Alex Morgan"
              className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated focus:border-accent focus:outline-none text-xs font-medium placeholder:text-muted"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider">
              Email Address
            </label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder="elena.rostova@example.com"
              className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated focus:border-accent focus:outline-none text-xs font-medium placeholder:text-muted"
            />
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-semibold text-muted uppercase tracking-wider">
              Password
            </label>
            <input
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (errorMessage) setErrorMessage(null);
              }}
              placeholder="Min. 8 characters"
              className="w-full px-3.5 py-2.5 rounded-sm border border-subtle text-ink bg-elevated focus:border-accent focus:outline-none text-xs font-medium placeholder:text-muted"
            />
          </div>

          <Button
            type="submit"
            disabled={isLoading}
            isLoading={isLoading}
            variant="primary"
            size="md"
            rightIcon={<ArrowRight className="w-4 h-4" />}
            className="w-full justify-center font-semibold mt-4"
          >
            Register Account
          </Button>
        </form>

        <div className="mt-8 pt-6 border-t border-subtle text-center text-xs text-muted font-medium">
          Already have an account?{' '}
          <Link to="/login" className="font-semibold text-accent hover:underline">
            Log In
          </Link>
        </div>
      </div>
    </div>
  );
};
