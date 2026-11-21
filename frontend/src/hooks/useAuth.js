// Auth context. This file avoids JSX on purpose (Vite only allows JSX in .jsx files).
import { createContext, createElement, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { clearSession, getStoredUser, getToken, saveSession } from "../services/api";
import * as authService from "../services/authService";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => getToken());
  const [username, setUsername] = useState(() => getStoredUser());

  const login = useCallback(async (user, password) => {
    const data = await authService.login(user, password);
    saveSession(data.access_token, data.username);
    setToken(data.access_token);
    setUsername(data.username);
  }, []);

  const logout = useCallback(() => {
    clearSession();
    setToken(null);
    setUsername(null);
  }, []);

  // The API client fires this event when the server says the session has expired.
  useEffect(() => {
    const onExpired = () => {
      setToken(null);
      setUsername(null);
    };
    window.addEventListener("ecv-auth-expired", onExpired);
    return () => window.removeEventListener("ecv-auth-expired", onExpired);
  }, []);

  const value = useMemo(
    () => ({ isAuthenticated: Boolean(token), username, login, logout }),
    [token, username, login, logout]
  );

  return createElement(AuthContext.Provider, { value }, children);
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}