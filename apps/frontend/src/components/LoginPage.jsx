import React, { useState } from "react";
import { motion } from "framer-motion";
import { LockKeyhole, Mail, Building2, ArrowRight } from "lucide-react";
import { Scene } from "../components/ui/hero-section";

export default function LoginPage({ onSubmit, isLoading = false, error = "" }) {
  const [form, setForm] = useState({
    email: "admin@test-company.dev",
    password: "admin123",
    tenantSlug: "test-company",
  });

  const updateField = (key, value) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    await onSubmit(form);
  };

  return (
    <div className="min-h-screen bg-black text-white overflow-hidden relative">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <Scene />
      </div>

      <div className="relative z-10 min-h-screen flex items-center justify-center px-6 py-10">
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-[1.15fr_0.85fr] gap-10 items-center">
          <motion.div
            initial={{ opacity: 0, x: -24 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.5 }}
            className="hidden lg:block"
          >
            <div className="max-w-2xl">
              <div className="text-[11px] uppercase tracking-[0.6em] text-white/40 font-semibold mb-6">
                VIKKI / SECURE ACCESS
              </div>

              <h1 className="text-7xl font-extralight tracking-tighter leading-none">
                Виктор
                <span className="text-vikki-accent drop-shadow-[0_0_20px_rgba(0,210,255,0.6)]">
                  .
                </span>
              </h1>

              <p className="mt-8 max-w-xl text-white/55 text-lg leading-relaxed">
                Авторизация в рабочий контур Vikki. После входа UI будет читать
                реальные данные из локального API: аналитику, транзакции и события.
              </p>

              <div className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4">
                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                  <div className="text-[10px] uppercase tracking-[0.22em] text-white/30 font-black mb-3">
                    Tenant
                  </div>
                  <div className="text-white/80 font-semibold">test-company</div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                  <div className="text-[10px] uppercase tracking-[0.22em] text-white/30 font-black mb-3">
                    Access
                  </div>
                  <div className="text-white/80 font-semibold">JWT Bearer</div>
                </div>

                <div className="rounded-3xl border border-white/10 bg-white/[0.04] p-5">
                  <div className="text-[10px] uppercase tracking-[0.22em] text-white/30 font-black mb-3">
                    Source
                  </div>
                  <div className="text-white/80 font-semibold">Local API</div>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.45 }}
            className="w-full max-w-xl mx-auto"
          >
            <div className="rounded-[40px] border border-white/10 bg-white/[0.05] backdrop-blur-3xl shadow-2xl p-8 sm:p-10">
              <div className="mb-8">
                <div className="text-[11px] uppercase tracking-[0.3em] text-white/35 font-black mb-4">
                  Авторизация
                </div>
                <h2 className="text-3xl font-light tracking-tight">Вход в Vikki</h2>
              </div>

              <form onSubmit={handleSubmit} className="space-y-5">
                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-white/35 font-black">
                    <Mail size={14} className="text-vikki-accent" />
                    Email
                  </span>
                  <input
                    type="email"
                    value={form.email}
                    onChange={(e) => updateField("email", e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-4 outline-none focus:border-vikki-accent/60 text-white placeholder:text-white/20"
                    placeholder="admin@test-company.dev"
                    autoComplete="username"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-white/35 font-black">
                    <LockKeyhole size={14} className="text-vikki-accent" />
                    Пароль
                  </span>
                  <input
                    type="password"
                    value={form.password}
                    onChange={(e) => updateField("password", e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-4 outline-none focus:border-vikki-accent/60 text-white placeholder:text-white/20"
                    placeholder="••••••••"
                    autoComplete="current-password"
                  />
                </label>

                <label className="block">
                  <span className="mb-2 flex items-center gap-2 text-[11px] uppercase tracking-[0.22em] text-white/35 font-black">
                    <Building2 size={14} className="text-vikki-accent" />
                    Tenant slug
                  </span>
                  <input
                    type="text"
                    value={form.tenantSlug}
                    onChange={(e) => updateField("tenantSlug", e.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-4 outline-none focus:border-vikki-accent/60 text-white placeholder:text-white/20"
                    placeholder="test-company"
                  />
                </label>

                {error ? (
                  <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                    {error}
                  </div>
                ) : null}

                <button
                  type="submit"
                  disabled={isLoading}
                  className="w-full rounded-2xl bg-vikki-accent/90 hover:bg-vikki-accent text-black px-5 py-4 font-black uppercase tracking-[0.22em] transition-all disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                  <span>{isLoading ? "Вход..." : "Войти"}</span>
                  <ArrowRight size={16} />
                </button>
              </form>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}