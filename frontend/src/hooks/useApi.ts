import { useCallback } from 'react';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

interface ApiOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: FormData | string | null;
  requiresAuth?: boolean;
}

interface ApiError {
  detail: string;
  errors?: unknown[];
  error_code?: string;
}

export function useApi() {
  const getToken = (): string | null => {
    return localStorage.getItem('access_token');
  };

  const setToken = (token: string): void => {
    localStorage.setItem('access_token', token);
  };

  const removeToken = (): void => {
    localStorage.removeItem('access_token');
  };

  const request = useCallback(async <T = unknown>(
    endpoint: string,
    options: ApiOptions = {}
  ): Promise<T> => {
    const {
      method = 'GET',
      headers = {},
      body = null,
      requiresAuth = true
    } = options;

    const requestHeaders: Record<string, string> = {
      ...headers
    };

    if (requiresAuth) {
      const token = getToken();
      if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      }
    }

    if (body instanceof FormData) {
      // Don't set Content-Type for FormData, browser will set it with boundary
    } else if (body) {
      requestHeaders['Content-Type'] = 'application/json';
    }

    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method,
      headers: requestHeaders,
      body: body instanceof FormData ? body : body
    });

    if (!response.ok) {
      let errorData: ApiError;
      try {
        errorData = await response.json() as ApiError;
      } catch {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      throw new Error(errorData.detail || `Request failed with status ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json() as Promise<T>;
  }, []);

  return {
    request,
    getToken,
    setToken,
    removeToken,
    API_BASE_URL
  };
}
