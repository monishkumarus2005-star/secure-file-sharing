import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Auth } from './components/Auth';
import { FileDashboard } from './components/FileDashboard';
import { ForgotPassword } from './pages/ForgotPassword';
import { ResetPassword } from './pages/ResetPassword';
import { ShareDownload } from './pages/ShareDownload';
import { api } from './api';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          // A quick ping to confirm the user is valid before loading the dashboard
          await api.get('/users/me');
          setIsAuthenticated(true);
        } catch {
          // Interceptor will handle refresh automatically if possible, otherwise logs out
          if (!localStorage.getItem('access_token')) {
              setIsAuthenticated(false);
          }
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const handleAuthSuccess = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    setIsAuthenticated(false);
    // Token wiping is now handled inside useAuth.ts -> logout()
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100">
        <div className="flex flex-col items-center gap-4">
          <div className="w-12 h-12 border-4 border-primary/30 border-t-primary rounded-full animate-spin" />
          <p className="text-slate-500 font-medium">Loading Application...</p>
        </div>
      </div>
    );
  }

  return (
    <BrowserRouter>
        <Routes>
            {/* Public Routes */}
            <Route path="/share/:token" element={<ShareDownload />} />
            <Route path="/forgot-password" element={<ForgotPassword />} />
            <Route path="/reset-password" element={<ResetPassword />} />
            
            {/* Auth Gateway */}
            <Route 
                path="/login" 
                element={isAuthenticated ? <Navigate to="/" replace /> : <Auth onAuthSuccess={handleAuthSuccess} />} 
            />
            
            {/* Protected Routes */}
            <Route 
                path="/" 
                element={isAuthenticated ? <FileDashboard onLogout={handleLogout} /> : <Navigate to="/login" replace />} 
            />
            
            {/* Catch All redirect */}
            <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
    </BrowserRouter>
  );
}

export default App;
