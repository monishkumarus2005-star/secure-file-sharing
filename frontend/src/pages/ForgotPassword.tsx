import { useState } from 'react';
import { Mail, ArrowLeft, Shield } from 'lucide-react';
import { Link } from 'react-router-dom';
import { api } from '../api';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);
    
    try {
      await api.post('/auth/forgot-password', { email });
    } catch (e) {
      // Intentionally ignore errors to prevent user enumeration
      console.warn("Forgot password request completed", e);
    } finally {
      // Always show success message regardless of actual account existence
      setSuccess(true);
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
          <h1 className="text-2xl font-bold text-white mb-2 tracking-tight">Recover Password</h1>
        </div>

        {success ? (
            <div className="text-center space-y-6 flex flex-col items-center">
                <div className="p-4 bg-emerald-500/10 border border-emerald-500/20 rounded-xl text-emerald-400 text-sm font-medium">
                    If that email is registered, a reset link has been sent. Please check your inbox.
                </div>
                <Link to="/login" className="text-violet-400 hover:text-violet-300 transition-colors font-medium text-sm flex items-center gap-2 mt-4">
                    <ArrowLeft className="w-4 h-4" /> Return to Login
                </Link>
            </div>
        ) : (
            <form onSubmit={handleSubmit} className="space-y-6">
                <p className="text-sm text-slate-400 text-center mb-6">
                    Enter your email address and we'll send you a securely signed token to reset your password.
                </p>
                <div>
                    <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                        Account Email
                    </label>
                    <div className="relative">
                        <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                        <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                            py-3.5 pl-12 pr-4 rounded-lg border border-slate-700
                            focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                            transition-all duration-100"
                        placeholder="Enter your email"
                        required
                        />
                    </div>
                </div>

                <button
                    type="submit"
                    disabled={isSubmitting || !email}
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
                            <span>Sending Secure Link...</span>
                        </>
                    ) : (
                        <span>Send Reset Link</span>
                    )}
                </button>
                
                <div className="text-center mt-6">
                    <Link to="/login" className="text-slate-400 hover:text-violet-300 transition-colors font-medium text-sm inline-flex items-center gap-2">
                        <ArrowLeft className="w-4 h-4" /> Back to Login
                    </Link>
                </div>
            </form>
        )}
      </div>
    </div>
  );
}
