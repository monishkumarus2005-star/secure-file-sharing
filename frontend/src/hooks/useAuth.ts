import { useState, useCallback, useEffect } from 'react';
import { api } from '../api';
import { useNavigate } from 'react-router-dom';

export interface User {
  id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

interface LoginCredentials {
  username: string;
  password: string;
}

interface RegisterData {
  username: string;
  email: string;
  password: string;
  role?: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null);
  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Check authentication status on mount
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('access_token');
      if (token) {
        try {
          const response = await api.get<User>('/users/me');
          setUser(response.data);
          setIsAuthenticated(true);
        } catch {
          // Token invalid or expired (interceptor handles the refresh or redirect)
          setUser(null);
          setIsAuthenticated(false);
        }
      }
      setIsLoading(false);
    };

    checkAuth();
  }, []);

  const login = useCallback(async (credentials: LoginCredentials): Promise<void> => {
    setError(null);
    setIsLoading(true);

    try {
      // Create form data for OAuth2 password flow
      const formData = new URLSearchParams();
      formData.append('username', credentials.username);
      formData.append('password', credentials.password);

      const response = await api.post<TokenResponse>('/auth/login', formData.toString(), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded'
        }
      });

      const tokenData = response.data;
      
      // Store both tokens (FIX 4)
      localStorage.setItem('access_token', tokenData.access_token);
      if (tokenData.refresh_token) {
          localStorage.setItem('refresh_token', tokenData.refresh_token);
      }

      // Fetch user data
      const userResponse = await api.get<User>('/users/me');
      setUser(userResponse.data);
      setIsAuthenticated(true);
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Login failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, []);

  const register = useCallback(async (data: RegisterData): Promise<void> => {
    setError(null);
    setIsLoading(true);

    try {
      await api.post<User>('/register', data);
      // After successful registration, log the user in
      await login({ username: data.username, password: data.password });
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Registration failed';
      setError(errorMessage);
      throw err;
    } finally {
      setIsLoading(false);
    }
  }, [login]);

  const logout = useCallback(async (): Promise<void> => {
    // FIX 3: Logout hits blacklist
    try {
        const refreshToken = localStorage.getItem("refresh_token");
        if (refreshToken) {
            await api.post("/auth/logout", { 
                refresh_token: refreshToken 
            });
        }
    } catch (e) {
        console.warn("Logout API call failed:", e);
    } finally {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
        delete api.defaults.headers.common["Authorization"];
        navigate("/login");
        setUser(null);
        setIsAuthenticated(false);
        setError(null);
    }
  }, [navigate]);

  return {
    user,
    isAuthenticated,
    isLoading,
    error,
    login,
    register,
    logout
  };
}
