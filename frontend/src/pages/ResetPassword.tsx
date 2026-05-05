import { useState, useEffect } from 'react';
import { Lock, Shield, AlertTriangle, CheckCircle } from 'lucide-react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { api } from '../api';

export function ResetPassword() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get("token");

  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<{type: 'error'|'success', text: string} | null>(null);

  useEffect(() => {
      if (!token) {
          setStatusMsg({type: 'error', text: 'No reset token provided in the URL link.'});
      }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (password !== confirmPassword) {
        setStatusMsg({type: 'error', text: 'Passwords do not match. Please verify.'});
        return;
    }

    if (!token) return;

    setIsSubmitting(true);
    setStatusMsg(null);
    
    try {
      await api.post('/auth/reset-password', { token, new_password: password });
      setStatusMsg({type: 'success', text: 'Password reset completely successfully. Redirecting shortly...'});
      setTimeout(() => navigate("/login"), 2500);
    } catch (e: any) {
      console.error(e);
      setStatusMsg({type: 'error', text: 'This link has expired or has already been used.'});
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div className="w-full max-w-md bg-slate-900 rounded-2xl p-10 shadow-[0_25px_50px_-12px_rgba(124,58,237,0.25)] border border-slate-800">
        
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-violet-500/10 rounded-2xl mb-6">
            <Shield className="w-8 h-8 text-violet-500" />
          </div>
          <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Set New Password</h1>
        </div>

        {statusMsg && (
            <div className={`mb-6 flex items-center gap-2 border rounded-lg px-4 py-3 ${statusMsg.type === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-400' : 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'}`}>
                {statusMsg.type === 'error' ? <AlertTriangle className="w-4 h-4 flex-shrink-0" /> : <CheckCircle className="w-4 h-4 flex-shrink-0" />}
                <span className="text-sm font-medium">{statusMsg.text}</span>
            </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-6">
            <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    New Password
                </label>
                <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                        py-3.5 pl-12 pr-4 rounded-lg border border-slate-700
                        focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                        transition-all duration-100"
                    placeholder="Enter new password"
                    required
                    minLength={8}
                    />
                </div>
            </div>

            <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                    Confirm New Password
                </label>
                <div className="relative">
                    <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                    <input
                    type="password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                        py-3.5 pl-12 pr-4 rounded-lg border border-slate-700
                        focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                        transition-all duration-100"
                    placeholder="Confirm new password"
                    required
                    minLength={8}
                    />
                </div>
            </div>

            <button
                type="submit"
                disabled={isSubmitting || !token || !password || !confirmPassword || statusMsg?.type === 'success'}
                className="w-full flex items-center justify-center gap-2
                bg-violet-600 hover:bg-violet-500
                text-white font-bold py-4 px-6 rounded-lg
                transition-all duration-200 ease-out
                hover:scale-105 hover:shadow-[0_0_30px_rgba(124,58,237,0.4)]
                disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
            >
                {isSubmitting ? (
                    <>
                        <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Updating...</span>
                    </>
                ) : (
                    <span>Confirm Password Reset</span>
                )}
            </button>
        </form>
      </div>
    </div>
  );
}
