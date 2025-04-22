import { env } from '../config/env';
import { useAuth } from './auth-context';

export const API_CONFIG = {
  baseURL: env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
    ...(env.VITE_ACCESS_TOKEN && {
      Authorization: `Bearer ${env.VITE_ACCESS_TOKEN}`,
    }),
  },
} as const;

type ApiResponse<T = any> = Promise<Response>;

// Helper to get auth headers
const getAuthHeaders = async (): Promise<Headers> => {
  const headers = new Headers(API_CONFIG.headers);

  // Try to get the auth context from the global window object
  // This is a workaround since we can't use hooks outside of components
  if (window.__AUTH_CONTEXT__) {
    try {
      const token = await window.__AUTH_CONTEXT__.getToken();
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }
    } catch (error) {
      console.error('Error getting auth token:', error);
    }
  }

  return headers;
};

// Custom hook version of apiClient for use within React components
export const useApiClient = () => {
  const auth = useAuth();

  // Store auth in window for non-hook usage
  if (typeof window !== 'undefined') {
    window.__AUTH_CONTEXT__ = auth;
  }

  return {
    async get<T>(endpoint: string, params?: Record<string, any>): ApiResponse<T> {
      const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) =>
          url.searchParams.append(key, value)
        );
      }

      const token = await auth.getToken();
      const headers = new Headers(API_CONFIG.headers);
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return await fetch(url.toString(), {
        method: 'GET',
        headers,
      });
    },

    async post<T>(endpoint: string, data?: any, params?: Record<string, string>): ApiResponse<T> {
      const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) =>
          url.searchParams.append(key, value)
        );
      }

      const token = await auth.getToken();
      const headers = new Headers(API_CONFIG.headers);
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return await fetch(url.toString(), {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      });
    },

    async put<T>(endpoint: string, params?: Record<string, string>, data?: any): ApiResponse<T> {
      const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) =>
          url.searchParams.append(key, value)
        );
      }

      const token = await auth.getToken();
      const headers = new Headers(API_CONFIG.headers);
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return await fetch(url.toString(), {
        method: 'PUT',
        headers,
        body: data ? JSON.stringify(data) : undefined,
      });
    },

    async patch<T>(endpoint: string, data?: any, params?: Record<string, string>): ApiResponse<T> {
      const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) =>
          url.searchParams.append(key, value)
        );
      }

      const token = await auth.getToken();
      const headers = new Headers(API_CONFIG.headers);
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return await fetch(url.toString(), {
        method: 'PATCH',
        headers,
        body: JSON.stringify(data),
      });
    },

    async delete<T>(endpoint: string, params?: Record<string, string>): ApiResponse<T> {
      const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
      if (params) {
        Object.entries(params).forEach(([key, value]) =>
          url.searchParams.append(key, value)
        );
      }

      const token = await auth.getToken();
      const headers = new Headers(API_CONFIG.headers);
      if (token) {
        headers.set('Authorization', `Bearer ${token}`);
      }

      return await fetch(url.toString(), {
        method: 'DELETE',
        headers,
      });
    },
  };
};

// For backwards compatibility
// This is a non-hook version that still tries to get auth from the window
export const apiClient = {
  async get<T>(endpoint: string, params?: Record<string, any>): ApiResponse<T> {
    const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) =>
        url.searchParams.append(key, value)
      );
    }

    const headers = await getAuthHeaders();

    return await fetch(url.toString(), {
      method: 'GET',
      headers,
    });
  },

  async post<T>(endpoint: string, data?: any, params?: Record<string, string>): ApiResponse<T> {
    const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) =>
        url.searchParams.append(key, value)
      );
    }

    const headers = await getAuthHeaders();

    return await fetch(url.toString(), {
      method: 'POST',
      headers,
      body: JSON.stringify(data),
    });
  },

  async put<T>(endpoint: string, params?: Record<string, string>, data?: any): ApiResponse<T> {
    const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) =>
        url.searchParams.append(key, value)
      );
    }

    const headers = await getAuthHeaders();

    return await fetch(url.toString(), {
      method: 'PUT',
      headers,
      body: data ? JSON.stringify(data) : undefined,
    });
  },

  async patch<T>(endpoint: string, data?: any, params?: Record<string, string>): ApiResponse<T> {
    const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) =>
        url.searchParams.append(key, value)
      );
    }

    const headers = await getAuthHeaders();

    return await fetch(url.toString(), {
      method: 'PATCH',
      headers,
      body: JSON.stringify(data),
    });
  },

  async delete<T>(endpoint: string, params?: Record<string, string>): ApiResponse<T> {
    const url = new URL(`${API_CONFIG.baseURL}${endpoint}`);
    if (params) {
      Object.entries(params).forEach(([key, value]) =>
        url.searchParams.append(key, value)
      );
    }

    const headers = await getAuthHeaders();

    return await fetch(url.toString(), {
      method: 'DELETE',
      headers,
    });
  },
};
