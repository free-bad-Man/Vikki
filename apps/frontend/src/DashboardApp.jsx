import React, { useEffect, useMemo, useState } from "react";
import {
  motion,
  AnimatePresence,
  useMotionValue,
  useTransform,
  animate,
} from "framer-motion";
import Layout from "./components/Layout";
import VikkiInput from "./components/VikkiInput";
import EdoWidget from "./components/EdoWidget";
import { Scene } from "./components/ui/hero-section";
import {
  Receipt,
  Eye,
  EyeOff,
  Activity,
  Clock,
  TrendingUp,
  Sparkles,
  Box,
  AlertTriangle,
  RefreshCw,
  LogOut,
} from "lucide-react";
import {
  loadDashboard,
  loadTransactions,
  loadNotifications,
  formatCurrency,
  formatCompactNumber,
  formatDateTime,
  formatDayLabel,
  truncate,
  toSignedAmount,
  notificationTone,
} from "./lib/api";

const Counter = ({ value, isPrivacy }) => {
  const count = useMotionValue(0);
  const rounded = useTransform(count, (latest) =>
    new Intl.NumberFormat("ru-RU", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(latest)
  );

  useEffect(() => {
    const controls = animate(count, Number(value || 0), {
      duration: 2.5,
      ease: [0.16, 1, 0.3, 1],
    });
    return controls.stop;
  }, [count, value]);

  return (
    <motion.span
      className={
        isPrivacy
          ? "blur-2xl opacity-10 transition-all duration-500"
          : "transition-all duration-500"
      }
    >
      <motion.span>{rounded}</motion.span>
    </motion.span>
  );
};

const PanelError = ({ message }) => (
  <div className="h-full flex items-center justify-center border border-dashed border-red-500/20 rounded-3xl px-6 text-center">
    <div className="space-y-3">
      <AlertTriangle size={22} className="mx-auto text-red-400" />
      <p className="text-[11px] text-red-300/80 uppercase font-bold tracking-[0.18em] leading-relaxed">
        {message}
      </p>
    </div>
  </div>
);

const PanelEmpty = ({ message }) => (
  <div className="h-full flex items-center justify-center border border-dashed border-white/10 rounded-3xl">
    <span className="text-[10px] text-white/20 uppercase font-bold tracking-[0.3em] text-center px-6">
      {message}
    </span>
  </div>
);

const SummaryRow = ({ label, value, tone = "default", blur = false }) => {
  const toneClass =
    tone === "accent"
      ? "text-vikki-accent"
      : tone === "success"
      ? "text-vikki-up"
      : tone === "danger"
      ? "text-red-400"
      : "text-white/80";

  return (
    <div className="flex items-center justify-between py-3 border-b border-white/5 last:border-b-0">
      <span className="text-[11px] uppercase tracking-[0.22em] text-white/35 font-black">
        {label}
      </span>
      <span className={`text-sm font-mono font-black ${toneClass} ${blur ? "blur-md" : ""}`}>
        {value}
      </span>
    </div>
  );
};

const EventItem = ({ item }) => {
  const tone = notificationTone(item.notification_type);

  const borderClass =
    tone === "success"
      ? "border-l-vikki-up"
      : tone === "warning"
      ? "border-l-amber-400"
      : tone === "error"
      ? "border-l-red-500"
      : "border-l-vikki-accent";

  const titleClass =
    tone === "success"
      ? "text-vikki-up"
      : tone === "warning"
      ? "text-amber-300"
      : tone === "error"
      ? "text-red-400"
      : "text-vikki-accent";

  return (
    <div className={`p-5 bg-white/[0.05] rounded-3xl border border-white/5 border-l-4 ${borderClass}`}>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className={`text-[11px] uppercase tracking-[0.24em] font-black mb-2 ${titleClass}`}>
            {truncate(item.title || "Событие", 42)}
          </p>
          <p className="text-[12px] text-white/60 leading-relaxed font-semibold">
            {truncate(item.message || "Нет деталей события", 120)}
          </p>
        </div>
        {!item.is_read && (
          <span className="mt-1 w-2 h-2 rounded-full bg-vikki-accent shadow-[0_0_12px_#00d2ff] shrink-0" />
        )}
      </div>
      <div className="mt-3 text-[10px] uppercase tracking-[0.22em] text-white/25 font-black">
        {formatDateTime(item.created_at)}
      </div>
    </div>
  );
};

export default function DashboardApp({ currentUser, onLogout }) {
  const [uptime, setUptime] = useState("00:00:00");
  const [isPrivacy, setIsPrivacy] = useState(false);
  const [isInputFocused, setIsInputFocused] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [hoveredBar, setHoveredBar] = useState(null);

  const [dashboard, setDashboard] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [localEvents, setLocalEvents] = useState([]);

  const [loading, setLoading] = useState({
    dashboard: true,
    transactions: true,
    notifications: true,
  });

  const [errors, setErrors] = useState({
    dashboard: null,
    transactions: null,
    notifications: null,
  });

  const refreshAll = async ({ silent = false } = {}) => {
    if (!silent) {
      setLoading({
        dashboard: true,
        transactions: true,
        notifications: true,
      });
    }

    const [dashboardResult, transactionsResult, notificationsResult] =
      await Promise.allSettled([
        loadDashboard(7),
        loadTransactions({ limit: 12 }),
        loadNotifications({ limit: 10 }),
      ]);

    if (dashboardResult.status === "fulfilled") {
      setDashboard(dashboardResult.value);
      setErrors((prev) => ({ ...prev, dashboard: null }));
    } else {
      setErrors((prev) => ({
        ...prev,
        dashboard: dashboardResult.reason?.message || "Не удалось загрузить дашборд.",
      }));
    }

    if (transactionsResult.status === "fulfilled") {
      setTransactions(transactionsResult.value?.items || []);
      setErrors((prev) => ({ ...prev, transactions: null }));
    } else {
      setErrors((prev) => ({
        ...prev,
        transactions: transactionsResult.reason?.message || "Не удалось загрузить транзакции.",
      }));
    }

    if (notificationsResult.status === "fulfilled") {
      setNotifications(notificationsResult.value?.items || []);
      setErrors((prev) => ({ ...prev, notifications: null }));
    } else {
      setErrors((prev) => ({
        ...prev,
        notifications:
          notificationsResult.reason?.message || "Не удалось загрузить уведомления.",
      }));
    }

    setLoading({
      dashboard: false,
      transactions: false,
      notifications: false,
    });
  };

  useEffect(() => {
    const timer = setInterval(() => {
      setUptime(new Date().toLocaleTimeString("ru-RU"));
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    refreshAll();
    const poller = setInterval(() => {
      refreshAll({ silent: true });
    }, 60000);

    return () => clearInterval(poller);
  }, []);

  const handleVikkiAction = (message) => {
    setIsProcessing(true);

    setLocalEvents((prev) => [
      {
        id: `ui-${Date.now()}`,
        title: "Командный запрос принят",
        message: `UI принял запрос: "${message}". LLM endpoint пока не подключён к этому экрану.`,
        notification_type: "info",
        is_read: false,
        created_at: new Date().toISOString(),
      },
      ...prev,
    ].slice(0, 4));

    setTimeout(() => {
      setIsProcessing(false);
    }, 1200);
  };

  const summary = dashboard?.financial_summary || {
    total_income: 0,
    total_outcome: 0,
    balance: 0,
    bank_accounts_count: 0,
    transactions_count: 0,
  };

  const cashFlowData = useMemo(() => {
    const raw = dashboard?.cash_flow || [];

    return raw.map((item) => ({
      day: formatDayLabel(item.date),
      date: item.date,
      in: Number(item.income || 0),
      out: Number(item.outcome || 0),
      forecast: false,
    }));
  }, [dashboard]);

  const maxVal = useMemo(() => {
    const values = cashFlowData.flatMap((item) => [item.in, item.out]);
    return Math.max(1, ...values);
  }, [cashFlowData]);

  const topCounterparties = dashboard?.top_counterparties || [];

  const sbisDocs = useMemo(() => {
    return notifications
      .filter(
        (item) =>
          item.related_type === "sbis_document" ||
          String(item.title || "").toLowerCase().includes("сбис")
      )
      .slice(0, 6);
  }, [notifications]);

  const activityFeed = useMemo(() => {
    return [...localEvents, ...notifications]
      .sort((a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0))
      .slice(0, 5);
  }, [localEvents, notifications]);

  const unreadCount = useMemo(
    () => notifications.filter((item) => !item.is_read).length,
    [notifications]
  );

  const balanceTone =
    Number(summary.balance || 0) >= 0 ? "text-vikki-up" : "text-red-400";

  const balanceChipTone =
    Number(summary.balance || 0) >= 0
      ? "text-vikki-up bg-vikki-up/10 border-vikki-up/20"
      : "text-red-400 bg-red-500/10 border-red-500/20";

  return (
    <Layout>
      <div className="fixed inset-0 z-0 pointer-events-none">
        <Scene />
      </div>

      <div className="fixed top-0 left-0 right-0 h-12 border-b border-white/10 bg-black/60 backdrop-blur-3xl z-[100] flex items-center justify-between px-10 text-[10px] uppercase tracking-widest font-mono">
        <div className="flex gap-6 items-center ml-16">
          <span className="flex items-center gap-2 text-white/70">
            <motion.div
              animate={isProcessing ? { opacity: [0.5, 1, 0.5], scale: [1, 1.3, 1] } : {}}
              transition={{ repeat: Infinity, duration: 1.5 }}
              className="w-1.5 h-1.5 rounded-full bg-vikki-accent shadow-[0_0_10px_#00d2ff]"
            />
            СТАТУС:
            <span className="font-bold text-vikki-accent uppercase">
              {isProcessing ? "АНАЛИЗ..." : "АКТИВЕН"}
            </span>
          </span>

          <button
            onClick={() => refreshAll()}
            className="hover:text-vikki-accent transition-all flex items-center gap-2 cursor-pointer text-white/50"
          >
            <RefreshCw size={14} />
            <span>SYNC</span>
          </button>
        </div>

        <div className="flex items-center gap-8 text-white/60">
          <span className="hidden xl:block text-white/35 tracking-[0.18em]">
            {currentUser?.email}
          </span>

          <button
            onClick={() => setIsPrivacy(!isPrivacy)}
            className="hover:text-vikki-accent transition-all flex items-center gap-2 cursor-pointer"
          >
            {isPrivacy ? <EyeOff size={15} /> : <Eye size={15} />}
            <span>ПРИВАТНОСТЬ</span>
          </button>

          <button
            onClick={onLogout}
            className="hover:text-red-400 transition-all flex items-center gap-2 cursor-pointer"
          >
            <LogOut size={15} />
            <span>ВЫХОД</span>
          </button>

          <span className="text-white/40 font-bold tracking-[0.2em]">{uptime}</span>
        </div>
      </div>

      <main className="relative z-10 w-full min-h-screen pl-24 pt-28 pr-12 pb-20 flex flex-col items-center">
        <div className="w-full max-w-[1550px]">
          <header className="flex items-end justify-between mb-16 px-4 relative z-[60]">
            <div>
              <motion.h1
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                className="text-8xl font-extralight tracking-tighter text-white leading-none"
              >
                Виктор
                <span className="text-vikki-accent drop-shadow-[0_0_20px_rgba(0,210,255,0.6)]">
                  .
                </span>
              </motion.h1>
              <p className="text-white/40 mt-4 text-[11px] uppercase tracking-[0.7em] font-semibold">
                ИНТЕЛЛЕКТУАЛЬНАЯ ПАНЕЛЬ УПРАВЛЕНИЯ
              </p>
            </div>

            <div className="text-right">
              <div className={`text-7xl font-light tracking-tighter text-white drop-shadow-2xl ${balanceTone}`}>
                <Counter value={summary.balance} isPrivacy={isPrivacy} />
                <span className="text-base text-white/40 ml-3 uppercase font-mono tracking-widest">
                  ₽
                </span>
              </div>

              <div className="flex items-center justify-end gap-2 mt-3">
                <TrendingUp
                  size={14}
                  className={Number(summary.balance || 0) >= 0 ? "text-vikki-up" : "text-red-400"}
                />
                <div
                  className={`text-[11px] font-black tracking-widest py-1.5 px-3 rounded-lg border shadow-lg uppercase ${balanceChipTone}`}
                >
                  {Number(summary.balance || 0) >= 0 ? "+" : ""}
                  {formatCurrency(summary.balance)}
                </div>
              </div>
            </div>
          </header>

          <div
            className={`max-w-5xl mx-auto mb-20 px-4 relative z-[70] ${
              isInputFocused ? "opacity-70" : ""
            }`}
          >
            <div
              className={`bg-white/[0.05] backdrop-blur-[40px] rounded-3xl border border-white/10 transition-all duration-500 shadow-[0_0_50px_rgba(0,0,0,0.3)] ${
                isProcessing ? "border-amber-500/50 ring-1 ring-amber-500/20" : ""
              }`}
            >
              <div className="relative flex items-center">
                <div className="pl-6">
                  <motion.div
                    animate={isProcessing ? { opacity: [0.5, 1, 0.5], scale: [1, 1.2, 1] } : {}}
                    transition={{ repeat: Infinity, duration: 2 }}
                    className="p-2 rounded-xl bg-vikki-accent/10 border border-vikki-accent/30"
                  >
                    <Sparkles
                      size={22}
                      className={isProcessing ? "text-amber-400" : "text-vikki-accent"}
                    />
                  </motion.div>
                </div>

                <div className="flex-1">
                  <VikkiInput
                    onSendMessage={handleVikkiAction}
                    onFocusChange={(focused) => setIsInputFocused(focused)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div
            className={`grid grid-cols-12 gap-10 transition-all duration-700 ${
              isInputFocused ? "blur-xl opacity-30 scale-[0.98]" : ""
            }`}
          >
            <div className="col-span-3 flex flex-col gap-10">
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Receipt size={18} className="text-vikki-accent" /> ДОКУМЕНТЫ (СБИС)
                </div>

                <div className="flex-1 overflow-y-auto custom-scrollbar">
                  <EdoWidget
                    hideHeader
                    items={sbisDocs}
                    isLoading={loading.notifications}
                    error={errors.notifications}
                  />
                </div>
              </div>

              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Box size={18} className="text-vikki-accent" /> ФИНАНСОВАЯ СВОДКА
                </div>

                {errors.dashboard ? (
                  <PanelError message={errors.dashboard} />
                ) : (
                  <div className="flex-1 flex flex-col justify-between">
                    <div className="space-y-1">
                      <SummaryRow
                        label="Доход"
                        value={formatCurrency(summary.total_income)}
                        tone="success"
                        blur={isPrivacy}
                      />
                      <SummaryRow
                        label="Расход"
                        value={formatCurrency(summary.total_outcome)}
                        tone="danger"
                        blur={isPrivacy}
                      />
                      <SummaryRow
                        label="Счетов"
                        value={formatCompactNumber(summary.bank_accounts_count)}
                        tone="accent"
                      />
                      <SummaryRow
                        label="Операций"
                        value={formatCompactNumber(summary.transactions_count)}
                      />
                    </div>

                    <div className="mt-8 rounded-3xl border border-white/5 bg-white/[0.04] p-5">
                      <div className="text-[10px] uppercase tracking-[0.24em] text-white/30 font-black mb-3">
                        Непрочитанные события
                      </div>
                      <div className={`text-4xl font-light ${unreadCount > 0 ? "text-vikki-accent" : "text-white/70"}`}>
                        {formatCompactNumber(unreadCount)}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>

            <div className="col-span-6 flex flex-col gap-10">
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-10 h-[420px] border border-white/5 flex flex-col shadow-2xl relative overflow-visible">
                <div className="flex justify-between items-center mb-8 text-[10px] opacity-60 uppercase tracking-[0.3em] font-black text-white relative z-20">
                  <span>АНАЛИЗ ДЕНЕЖНЫХ ПОТОКОВ</span>
                  <div className="flex gap-6">
                    <span className="flex items-center gap-2 font-mono">
                      <div className="w-2 h-2 bg-vikki-accent rounded-full shadow-[0_0_10px_#00d2ff]" />
                      ПРИХОД
                    </span>
                    <span className="flex items-center gap-2 font-mono">
                      <div className="w-2 h-2 bg-red-500 rounded-full shadow-[0_0_10px_#ef4444]" />
                      РАСХОД
                    </span>
                  </div>
                </div>

                {errors.dashboard ? (
                  <PanelError message={errors.dashboard} />
                ) : cashFlowData.length === 0 ? (
                  <PanelEmpty message="Нет cash flow данных за выбранный период" />
                ) : (
                  <div className="flex-1 flex items-end justify-between gap-6 px-4 relative z-10">
                    {cashFlowData.map((d, i) => (
                      <div key={`${d.date}-${i}`} className="flex-1 flex flex-col items-center h-full justify-end group/item">
                        <div className="flex items-end gap-2 w-full h-[220px] justify-center relative">
                          <div className="relative flex flex-col items-center h-full justify-end">
                            <motion.span className="text-[10px] font-mono font-bold text-vikki-accent mb-2 group-hover/item:scale-125 transition-transform">
                              {Math.round(d.in / 1000)}k
                            </motion.span>
                            <motion.div
                              initial={{ height: 0 }}
                              animate={{ height: `${(d.in / maxVal) * 100}%` }}
                              onHoverStart={() => setHoveredBar({ day: d.day, type: "Приход", value: d.in })}
                              onHoverEnd={() => setHoveredBar(null)}
                              className="w-7 rounded-t-xl transition-all duration-500 cursor-pointer hover:brightness-150 bg-gradient-to-t from-vikki-accent/20 to-vikki-accent"
                            />
                          </div>

                          <div className="relative flex flex-col items-center h-full justify-end">
                            <motion.span className="text-[10px] font-mono font-bold text-red-500 mb-2 group-hover/item:scale-125 transition-transform">
                              {Math.round(d.out / 1000)}k
                            </motion.span>
                            <motion.div
                              initial={{ height: 0 }}
                              animate={{ height: `${(d.out / maxVal) * 100}%` }}
                              onHoverStart={() => setHoveredBar({ day: d.day, type: "Расход", value: d.out })}
                              onHoverEnd={() => setHoveredBar(null)}
                              className="w-7 rounded-t-xl transition-all duration-500 cursor-pointer hover:brightness-150 bg-gradient-to-t from-red-500/20 to-red-500"
                            />
                          </div>
                        </div>

                        <span className="text-[10px] opacity-40 mt-6 font-black tracking-widest text-white">
                          {d.day}
                        </span>
                      </div>
                    ))}

                    <AnimatePresence>
                      {hoveredBar && (
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          exit={{ opacity: 0, y: 10 }}
                          className="absolute -top-10 left-1/2 -translate-x-1/2 bg-black/90 backdrop-blur-3xl border border-white/10 p-5 rounded-2xl z-[100] shadow-2xl min-w-[180px]"
                        >
                          <div className="text-[9px] text-white/30 uppercase font-black mb-1 tracking-widest">
                            {hoveredBar.day} • {hoveredBar.type}
                          </div>
                          <div
                            className={`text-xl font-mono font-bold ${
                              hoveredBar.type === "Приход" ? "text-vikki-accent" : "text-red-500"
                            }`}
                          >
                            {formatCurrency(hoveredBar.value)}
                          </div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </div>

              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[810px] border border-white/5 flex flex-col shadow-2xl">
                <div className="flex justify-between items-center mb-6 text-[10px] opacity-60 uppercase tracking-[0.2em] font-black text-white">
                  <span>ЖУРНАЛ БАНКОВСКИХ ОПЕРАЦИЙ</span>
                  <Activity size={18} className="text-vikki-accent" />
                </div>

                {errors.transactions ? (
                  <PanelError message={errors.transactions} />
                ) : loading.transactions ? (
                  <div className="space-y-3 overflow-y-auto flex-1 custom-scrollbar pr-2">
                    {Array.from({ length: 6 }).map((_, idx) => (
                      <div
                        key={idx}
                        className="h-[78px] rounded-3xl border border-white/5 bg-white/[0.04] animate-pulse"
                      />
                    ))}
                  </div>
                ) : transactions.length === 0 ? (
                  <PanelEmpty message="Нет транзакций для отображения" />
                ) : (
                  <div className="space-y-3 overflow-y-auto flex-1 custom-scrollbar pr-2">
                    {transactions.map((t) => {
                      const incoming = t.transaction_type === "incoming";
                      const title =
                        t.counterparty_name || t.description || "Без названия операции";

                      return (
                        <div
                          key={t.id}
                          className="p-5 bg-white/[0.04] border border-white/5 rounded-3xl hover:bg-white/[0.08] transition-all"
                        >
                          <div className="flex items-start justify-between gap-6">
                            <div className="min-w-0">
                              <div className="text-[14px] font-semibold text-white/80">
                                {truncate(title, 54)}
                              </div>
                              <div className="mt-2 text-[11px] uppercase tracking-[0.18em] text-white/25 font-black">
                                {formatDateTime(t.occurred_at)}
                              </div>
                              {t.description && t.description !== title && (
                                <div className="mt-3 text-[12px] text-white/45 leading-relaxed">
                                  {truncate(t.description, 120)}
                                </div>
                              )}
                            </div>

                            <div className="text-right shrink-0">
                              <div
                                className={`text-base font-mono font-black ${
                                  isPrivacy ? "blur-md" : ""
                                } ${incoming ? "text-vikki-up" : "text-white/60"}`}
                              >
                                {toSignedAmount(t.amount, t.transaction_type)}
                              </div>
                              <div className="mt-2 text-[10px] uppercase tracking-[0.18em] text-white/25 font-black">
                                {t.currency || "RUB"}
                              </div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            <div className="col-span-3 flex flex-col gap-10">
              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Clock size={18} className="text-vikki-accent" /> ЖУРНАЛ СОБЫТИЙ
                </div>

                {errors.notifications ? (
                  <PanelError message={errors.notifications} />
                ) : activityFeed.length === 0 ? (
                  <PanelEmpty message="Нет событий для отображения" />
                ) : (
                  <div className="space-y-4 overflow-y-auto custom-scrollbar pr-1">
                    {activityFeed.map((item) => (
                      <EventItem key={item.id} item={item} />
                    ))}
                  </div>
                )}
              </div>

              <div className="bg-white/[0.03] backdrop-blur-2xl rounded-[40px] p-8 h-[340px] border border-white/5 flex flex-col shadow-2xl relative overflow-hidden">
                <div className="flex items-center gap-3 opacity-60 mb-6 text-[10px] uppercase tracking-[0.2em] font-black text-white">
                  <Box size={18} className="text-vikki-accent" /> ТОП КОНТРАГЕНТОВ
                </div>

                {errors.dashboard ? (
                  <PanelError message={errors.dashboard} />
                ) : topCounterparties.length === 0 ? (
                  <PanelEmpty message="Нет данных по контрагентам" />
                ) : (
                  <div className="space-y-4 overflow-y-auto custom-scrollbar pr-1">
                    {topCounterparties.map((item, index) => {
                      const net = Number(item.total_income || 0) - Number(item.total_outcome || 0);

                      return (
                        <div
                          key={`${item.counterparty_name}-${index}`}
                          className="p-5 bg-white/[0.05] rounded-3xl border border-white/5"
                        >
                          <div className="text-[11px] uppercase tracking-[0.22em] text-white/25 font-black mb-2">
                            {index + 1}
                          </div>
                          <div className="text-sm font-semibold text-white/80">
                            {truncate(item.counterparty_name, 44)}
                          </div>

                          {item.counterparty_inn && (
                            <div className="mt-2 text-[10px] uppercase tracking-[0.18em] text-white/25 font-black">
                              ИНН {item.counterparty_inn}
                            </div>
                          )}

                          <div className="mt-4 flex items-center justify-between text-[11px] uppercase tracking-[0.16em]">
                            <span className="text-white/30 font-black">Сделок</span>
                            <span className="text-white/70 font-mono font-black">
                              {formatCompactNumber(item.transactions_count)}
                            </span>
                          </div>

                          <div className="mt-2 flex items-center justify-between text-[11px] uppercase tracking-[0.16em]">
                            <span className="text-white/30 font-black">Net</span>
                            <span
                              className={`font-mono font-black ${
                                net >= 0 ? "text-vikki-up" : "text-red-400"
                              } ${isPrivacy ? "blur-md" : ""}`}
                            >
                              {formatCurrency(net)}
                            </span>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </main>
    </Layout>
  );
}