import React, { useEffect, useState } from "react";
import DashboardApp from "./DashboardApp";
import LoginPage from "./components/LoginPage";
import {
  clearStoredToken,
  fetchCurrentUser,
  getStoredToken,
  login,
  UNAUTHORIZED_EVENT,
} from "./lib/auth";

function BootScreen() {
  return (
    <div className="min-h-screen bg-black flex items-center justify-center text-white">
      <div className="text-center">
        <div className="text-[11px] uppercase tracking-[0.35em] text-white/35 font-black mb-4">
          VIKKI / AUTH
        </div>
        <div className="text-2xl font-light">Проверка сессии...</div>
      </div>
    </div>
  );
}

export default function App() {
  const [booting, setBooting] = useState(true);
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [currentUser, setCurrentUser] = useState(null);

  useEffect(() => {
    const boot = async () => {
      const token = getStoredToken();

      if (!token) {
        setBooting(false);
        return;
      }

      try {
        const user = await fetchCurrentUser();
        setCurrentUser(user);
      } catch {
        clearStoredToken();
        setCurrentUser(null);
      } finally {
        setBooting(false);
      }
    };

    boot();
  }, []);

  useEffect(() => {
    const handleUnauthorized = () => {
      clearStoredToken();
      setCurrentUser(null);
      setAuthError("Сессия истекла. Войдите снова.");
    };

    window.addEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    return () => {
      window.removeEventListener(UNAUTHORIZED_EVENT, handleUnauthorized);
    };
  }, []);

  const handleLogin = async ({ email, password, tenantSlug }) => {
    setAuthLoading(true);
    setAuthError("");

    try {
      await login(email, password, tenantSlug);
      const user = await fetchCurrentUser();
      setCurrentUser(user);
    } catch (error) {
      setAuthError(error?.message || "Не удалось выполнить вход.");
      clearStoredToken();
      setCurrentUser(null);
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    clearStoredToken();
    setCurrentUser(null);
    setAuthError("");
  };

  if (booting) {
    return <BootScreen />;
  }

  if (!currentUser) {
    return (
      <LoginPage
        onSubmit={handleLogin}
        isLoading={authLoading}
        error={authError}
      />
    );
  }

  return <DashboardApp currentUser={currentUser} onLogout={handleLogout} />;
}