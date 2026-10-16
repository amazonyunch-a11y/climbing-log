import { authApi } from '@/src/api/auth';
import { setUnauthorizedHandler } from '@/src/api/client';
import { tokenStorage } from '@/src/auth/tokenStorage';
import type { CurrentUser, LoginRequest, SignupRequest } from '@/src/types/auth';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

type AuthContextValue = {
  user: CurrentUser | null;
  isLoading: boolean;
  login: (payload: LoginRequest) => Promise<void>;
  signup: (payload: SignupRequest) => Promise<void>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const clearSession = useCallback(async () => {
    await tokenStorage.clear();
    setUser(null);
  }, []);

  useEffect(() => {
    setUnauthorizedHandler(clearSession);
    return () => setUnauthorizedHandler(undefined);
  }, [clearSession]);

  useEffect(() => {
    async function restoreSession() {
      const token = await tokenStorage.get();
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        setUser(await authApi.me());
      } catch {
        await clearSession();
      } finally {
        setIsLoading(false);
      }
    }

    void restoreSession();
  }, [clearSession]);

  const login = useCallback(async (payload: LoginRequest) => {
    const token = await authApi.login(payload);
    await tokenStorage.set(token.access_token);
    try {
      setUser(await authApi.me());
    } catch (error) {
      await clearSession();
      throw error;
    }
  }, [clearSession]);

  const signup = useCallback(async (payload: SignupRequest) => {
    await authApi.signup(payload);
  }, []);

  const logout = useCallback(async () => {
    try {
      await authApi.logout();
    } finally {
      await clearSession();
    }
  }, [clearSession]);

  const value = useMemo(() => ({ user, isLoading, login, signup, logout }), [user, isLoading, login, signup, logout]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider.');
  return value;
}
