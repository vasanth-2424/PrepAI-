import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import type { LoginRequest, RegisterRequest, User } from '../types';
import { clearStoredToken, getStoredToken, setStoredToken } from './tokenStorage';

interface AuthContextValue {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  register: (payload: RegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const logout = useCallback(() => {
    api.clearToken();
    clearStoredToken();
    setUser(null);
    navigate('/login');
  }, [navigate]);

  useEffect(() => {
    api.setUnauthorizedHandler(() => {
      setUser(null);
      navigate('/login', { replace: true });
    });
  }, [navigate]);

  useEffect(() => {
    const token = getStoredToken();
    if (!token) {
      setIsLoading(false);
      return;
    }

    api.setToken(token);
    api
      .getMe()
      .then(setUser)
      .catch(() => {
        api.clearToken();
        clearStoredToken();
        setUser(null);
      })
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (payload: LoginRequest) => {
    const response = await api.login(payload);
    setStoredToken(response.access_token);
    api.setToken(response.access_token);
    const profile = await api.getMe();
    setUser(profile);
  }, []);

  const register = useCallback(async (payload: RegisterRequest) => {
    const response = await api.register(payload);
    setStoredToken(response.access_token);
    api.setToken(response.access_token);
    setUser(response.user);
  }, []);

  const value = useMemo(
    () => ({
      user,
      isAuthenticated: user !== null,
      isLoading,
      login,
      register,
      logout,
    }),
    [user, isLoading, login, register, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
