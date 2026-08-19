import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  clearAuthToken,
  getAuthToken,
  getMe,
  login as loginRequest,
  logoutRequest,
  setAuthToken,
  setUnauthorizedHandler,
} from "../api/client";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const navigate = useNavigate();
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(getAuthToken());
  const [loading, setLoading] = useState(true);

  const clearSession = useCallback(() => {
    clearAuthToken();
    setUser(null);
    setToken(null);
  }, []);

  const redirectToLogin = useCallback(
    (message) => {
      navigate("/login", {
        replace: true,
        state: message ? { message, kind: "auth" } : undefined,
      });
    },
    [navigate]
  );

  const logout = useCallback(async (options = {}) => {
    const { redirect = true, message } = options;
    try {
      const currentToken = getAuthToken();
      if (currentToken) {
        await logoutRequest();
      }
    } catch {
      // Token invalidation is client-side for JWT; ignore request failure
    } finally {
      clearSession();
      if (redirect) {
        redirectToLogin(message);
      }
    }
  }, [clearSession, redirectToLogin]);

  const login = useCallback(async (email, password) => {
    const data = await loginRequest(email, password);
    setAuthToken(data.access_token);
    setToken(data.access_token);
    try {
      const validatedUser = await getMe();
      setUser(validatedUser);
      return validatedUser;
    } catch (error) {
      clearSession();
      throw error;
    }
  }, [clearSession]);

  useEffect(() => {
    setUnauthorizedHandler(({ message } = {}) => {
      clearSession();
      redirectToLogin(message);
      return true;
    });
  }, [clearSession, redirectToLogin]);

  useEffect(() => {
    let active = true;

    const restoreSession = async () => {
      try {
        const storedToken = getAuthToken();
        if (!storedToken) {
          if (active) {
            setLoading(false);
          }
          return;
        }
        if (active) {
          setToken(storedToken);
        }
        const profile = await getMe();
        if (active) {
          setUser(profile);
        }
      } catch {
        clearSession();
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    restoreSession();
    return () => {
      active = false;
    };
  }, [clearSession]);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      logout,
      isAuthenticated: Boolean(user && token),
    }),
    [user, token, loading, login, logout]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return ctx;
};
