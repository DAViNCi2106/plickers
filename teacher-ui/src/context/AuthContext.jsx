/**
 * src/context/AuthContext.jsx
 * ===========================
 * Teacher authentication context provider.
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../api/client';

const initialUser = api.user;
const initialToken = api.accessToken;

const fallbackAuth = {
  user: initialUser,
  token: initialToken,
  isAuthenticated: !!initialToken,
  schoolId: initialUser?.school_id || 1,
  loading: false,
  login: async (email, password) => api.login(email, password),
  logout: () => api.clearSession(),
};

const AuthContext = createContext(fallbackAuth);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(api.user);
  const [token, setToken] = useState(api.accessToken);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function checkAuth() {
      if (api.accessToken) {
        try {
          const me = await api.getMe();
          setUser(me);
          api.user = me;
          localStorage.setItem('plickers_user', JSON.stringify(me));
        } catch {
          // If getMe fails, attempt token refresh before clearing
          try {
            const refreshed = await api.refreshAccessToken();
            if (refreshed) {
              const me = await api.getMe();
              setUser(me);
              api.user = me;
              setToken(api.accessToken);
              setLoading(false);
              return;
            }
          } catch (_) {}
          // Only clear if refresh fails
          api.clearSession();
          setUser(null);
          setToken(null);
        }
      }
      setLoading(false);
    }

    checkAuth();

    const handleExpired = () => {
      setUser(null);
      setToken(null);
    };
    window.addEventListener('auth:expired', handleExpired);
    return () => window.removeEventListener('auth:expired', handleExpired);
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    setUser(res.user);
    setToken(res.token?.access_token || api.accessToken);
    return res;
  };

  const logout = () => {
    api.clearSession();
    setUser(null);
    setToken(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        isAuthenticated: !!token,
        schoolId: user?.school_id || 1,
        loading,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  return ctx || fallbackAuth;
}
