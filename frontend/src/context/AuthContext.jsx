import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { getMe, login as loginRequest, logoutRequest, setUnauthorizedHandler } from "../api/client";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("campusai_token"));
  const [loading, setLoading] = useState(true);

  const logout = async () => {
    try {
      if (token) {
        await logoutRequest();
      }
    } catch {
      // Token invalidation is client-side for JWT; ignore request failure
    } finally {
      localStorage.removeItem("campusai_token");
      setUser(null);
      setToken(null);
    }
  };

  const login = async (email, password) => {
    const data = await loginRequest(email, password);
    localStorage.setItem("campusai_token", data.access_token);
    setToken(data.access_token);
    setUser(data.user);
    return data.user;
  };

  useEffect(() => {
    setUnauthorizedHandler(() => {
      localStorage.removeItem("campusai_token");
      setToken(null);
      setUser(null);
    });
  }, []);

  useEffect(() => {
    const restoreSession = async () => {
      try {
        const storedToken = localStorage.getItem("campusai_token");
        if (!storedToken) {
          setLoading(false);
          return;
        }
        setToken(storedToken);
        const profile = await getMe();
        setUser(profile);
      } catch {
        localStorage.removeItem("campusai_token");
        setToken(null);
        setUser(null);
      } finally {
        setLoading(false);
      }
    };

    restoreSession();
  }, []);

  const value = useMemo(
    () => ({
      user,
      token,
      loading,
      login,
      logout,
      isAuthenticated: Boolean(user && token),
    }),
    [user, token, loading]
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
