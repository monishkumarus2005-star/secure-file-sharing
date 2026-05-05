import { useState, useEffect } from 'react';
import { User, Lock, Mail, Eye, EyeOff, AlertCircle, Shield, Zap } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface AuthProps {
  onAuthSuccess: () => void;
}

export function Auth({ onAuthSuccess }: AuthProps) {
  const [isLogin, setIsLogin] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [isVisible, setIsVisible] = useState(false);
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: ''
  });

  const { login, register, isLoading, error } = useAuth();

  useEffect(() => {
    setIsVisible(true);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      if (isLogin) {
        await login({
          username: formData.username,
          password: formData.password
        });
      } else {
        if (formData.password !== formData.confirmPassword) {
          return;
        }
        await register({
          username: formData.username,
          email: formData.email,
          password: formData.password,
          role: 'user'
        });
      }
      onAuthSuccess();
    } catch {
      // Error is handled by the hook
    }
  };

  const toggleMode = () => {
    setIsLogin(!isLogin);
    setFormData({
      username: '',
      email: '',
      password: '',
      confirmPassword: ''
    });
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-950 p-4">
      <div 
        className={`w-full max-w-md bg-slate-900 rounded-2xl p-12 shadow-[0_25px_50px_-12px_rgba(124,58,237,0.25)] border border-slate-800
          transition-all duration-500 ease-out
          ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
      >
        {/* Header */}
        <div className="text-center mb-10">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-violet-500/10 rounded-2xl mb-6">
            <Shield className="w-8 h-8 text-violet-500" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-3 tracking-tight">
            {isLogin ? 'Welcome Back' : 'Create Account'}
          </h1>
          <p className="text-slate-400 text-sm">
            {isLogin
              ? 'Sign in to access your secure files'
              : 'Join our secure file sharing platform'}
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div className="mb-6 flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-lg px-4 py-3">
            <AlertCircle className="w-4 h-4 flex-shrink-0 text-red-400" />
            <span className="text-red-400 text-sm">{error}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Username */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Username
            </label>
            <div className="relative">
              <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                  py-3.5 pl-12 pr-4 rounded-lg
                  border border-slate-700
                  focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                  transition-all duration-100"
                placeholder="Enter your username"
                required
                minLength={3}
                maxLength={50}
              />
            </div>
          </div>

          {/* Email - Only for Sign Up */}
          {!isLogin && (
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Email
              </label>
              <div className="relative">
                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                    py-3.5 pl-12 pr-4 rounded-lg
                    border border-slate-700
                    focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                    transition-all duration-100"
                  placeholder="Enter your email"
                  required
                />
              </div>
            </div>
          )}

          {/* Password */}
          <div>
            <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Password
            </label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                  py-3.5 pl-12 pr-12 rounded-lg
                  border border-slate-700
                  focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                  transition-all duration-100"
                placeholder="Enter your password"
                required
                minLength={8}
                maxLength={72}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
              >
                {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
              </button>
            </div>
          </div>

          {/* Confirm Password - Only for Sign Up */}
          {!isLogin && (
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
                Confirm Password
              </label>
              <div className="relative">
                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-500" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={formData.confirmPassword}
                  onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                  className="w-full bg-slate-800 text-white font-medium placeholder-slate-500 
                    py-3.5 pl-12 pr-4 rounded-lg
                    border border-slate-700
                    focus:outline-none focus:ring-2 focus:ring-violet-500 focus:border-transparent
                    transition-all duration-100"
                  placeholder="Confirm your password"
                  required
                  minLength={8}
                />
              </div>
              {formData.password !== formData.confirmPassword && formData.confirmPassword && (
                <p className="text-red-400 text-sm mt-2">Passwords do not match</p>
              )}
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading || (!isLogin && formData.password !== formData.confirmPassword)}
            className="w-full flex items-center justify-center gap-2
              bg-violet-600 hover:bg-violet-500
              text-white font-bold
              py-4 px-6 rounded-lg
              transition-all duration-200 ease-out
              hover:scale-105 hover:shadow-[0_0_30px_rgba(124,58,237,0.4)]
              disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
          >
            {isLoading ? (
              <>
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                <span>{isLogin ? 'Signing In...' : 'Creating Account...'}</span>
              </>
            ) : (
              <>
                <span>{isLogin ? 'Sign In' : 'Create Account'}</span>
                <Zap className="w-5 h-5" />
              </>
            )}
          </button>
        </form>

        {isLogin && (
            <div className="mt-4 text-center">
                <Link to="/forgot-password" className="text-sm font-semibold text-slate-400 hover:text-violet-400 transition-colors">
                    Forgot your password?
                </Link>
            </div>
        )}

        {/* Toggle Mode */}
        <div className="mt-8 text-center">
          <p className="text-slate-400 text-sm">
            {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
            <button
              type="button"
              onClick={toggleMode}
              className="text-violet-400 hover:text-violet-300 font-semibold transition-colors"
            >
              {isLogin ? 'Sign Up' : 'Sign In'}
            </button>
          </p>
        </div>

        {/* Footer Security Badges */}
        <div className="mt-10 pt-8 border-t border-slate-800">
          <div className="flex items-center justify-center gap-6 text-xs text-slate-500">
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-emerald-500/60 rounded-full" />
              AES-128 Encryption
            </span>
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-emerald-500/60 rounded-full" />
              JWT Authentication
            </span>
            <span className="flex items-center gap-2">
              <div className="w-1.5 h-1.5 bg-emerald-500/60 rounded-full" />
              Blockchain Ready
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}
