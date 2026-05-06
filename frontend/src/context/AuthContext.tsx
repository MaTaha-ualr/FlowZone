import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import type { UserProfileResponse, RoleEnum } from "@/types";
import { getCurrentProfile, login as apiLogin, register as apiRegister } from "@/lib/api";

interface AuthState {
  user: UserProfileResponse | null;
  token: string | null;
  isAuthenticated: boolean;
  role: RoleEnum | null;
  isLoading: boolean;
}

interface AuthContextType extends AuthState {
  login: (username: string, password: string) => Promise<void>;
  register: (data: Record<string, unknown>) => Promise<void>;
  logout: () => void;
  refreshUser: () => Promise<void>;
  setAuth: (token: string, user: UserProfileResponse) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    token: null,
    isAuthenticated: false,
    role: null,
    isLoading: true,
  });

  const hydrate = useCallback(() => {
    try {
      const raw = localStorage.getItem("flowzone_auth");
      if (raw) {
        const parsed = JSON.parse(raw);
        setState({
          user: parsed.user ?? null,
          token: parsed.access_token ?? null,
          isAuthenticated: !!parsed.access_token,
          role: parsed.user?.role ?? null,
          isLoading: false,
        });
      } else {
        setState((s) => ({ ...s, isLoading: false }));
      }
    } catch {
      setState((s) => ({ ...s, isLoading: false }));
    }
  }, []);

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  const setAuth = useCallback((token: string, user: UserProfileResponse) => {
    const payload = { access_token: token, user };
    localStorage.setItem("flowzone_auth", JSON.stringify(payload));
    setState({
      user,
      token,
      isAuthenticated: true,
      role: user.role,
      isLoading: false,
    });
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const data = await apiLogin(username, password) as { access_token: string; user: UserProfileResponse };
    setAuth(data.access_token, data.user);
  }, [setAuth]);

  const register = useCallback(async (data: Record<string, unknown>) => {
    const response = await apiRegister(data) as { access_token?: string; user?: UserProfileResponse };
    if (response?.access_token && response?.user) {
      setAuth(response.access_token, response.user);
    }
  }, [setAuth]);

  const logout = useCallback(() => {
    localStorage.removeItem("flowzone_auth");
    setState({
      user: null,
      token: null,
      isAuthenticated: false,
      role: null,
      isLoading: false,
    });
    window.location.href = "#/login";
  }, []);

  const refreshUser = useCallback(async () => {
    if (!state.token || !state.user) return;
    try {
      const user = await getCurrentProfile() as UserProfileResponse;
      const payload = { access_token: state.token, user };
      localStorage.setItem("flowzone_auth", JSON.stringify(payload));
      setState((s) => ({ ...s, user, role: user.role }));
    } catch {
      localStorage.removeItem("flowzone_auth");
      setState({
        user: null,
        token: null,
        isAuthenticated: false,
        role: null,
        isLoading: false,
      });
    }
  }, [state.token, state.user]);

  return (
    <AuthContext.Provider value={{ ...state, login, register, logout, refreshUser, setAuth }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
