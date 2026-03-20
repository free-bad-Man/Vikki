import React from "react";
import GlassCard from "./GlassCard";
import { formatRelativeLabel, notificationTone, truncate } from "../lib/api";

const toneClassMap = {
  success: "border-vikki-up/20 text-vikki-up",
  warning: "border-amber-400/20 text-amber-300",
  error: "border-red-500/20 text-red-400",
  info: "border-vikki-accent/20 text-vikki-accent",
};

const resolveStatusLabel = (item) => {
  const title = (item?.title || "").toLowerCase();
  const tone = notificationTone(item?.notification_type);

  if (title.includes("подписан")) return "Подписан";
  if (title.includes("отклон")) return "Отклонён";
  if (title.includes("создан")) return "Создан";
  if (tone === "success") return "Успех";
  if (tone === "warning") return "Внимание";
  if (tone === "error") return "Ошибка";
  return "Новый";
};

const WidgetBody = ({ items, isLoading, error }) => {
  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, idx) => (
          <div
            key={idx}
            className="h-[68px] rounded-3xl border border-white/5 bg-white/[0.04] animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center border border-dashed border-red-500/20 rounded-3xl px-6 text-center">
        <span className="text-[11px] text-red-300/80 uppercase font-bold tracking-[0.25em] leading-relaxed">
          {error}
        </span>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="h-full flex items-center justify-center border border-dashed border-white/10 rounded-3xl">
        <span className="text-[10px] text-white/20 uppercase font-bold tracking-[0.3em]">
          Нет документов СБИС
        </span>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {items.map((doc) => {
        const tone = notificationTone(doc.notification_type);
        const statusLabel = resolveStatusLabel(doc);

        return (
          <div
            key={doc.id}
            className="flex items-center justify-between group/item cursor-default"
          >
            <div className="flex items-center space-x-4 min-w-0">
              <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center group-hover/item:bg-vikki-accent/20 transition-colors shrink-0">
                <span className="text-xs">📄</span>
              </div>

              <div className="min-w-0">
                <p className="text-sm font-light text-white/80 truncate">
                  {truncate(doc.title || doc.message || "Документ СБИС", 42)}
                </p>
                <p className="text-[10px] text-white/20 uppercase tracking-wider">
                  {formatRelativeLabel(doc.created_at)}
                </p>
              </div>
            </div>

            <span
              className={`text-[9px] px-2 py-1 rounded-full border shrink-0 ${
                toneClassMap[tone]
              }`}
            >
              {statusLabel}
            </span>
          </div>
        );
      })}
    </div>
  );
};

const EdoWidget = ({
  items = [],
  isLoading = false,
  error = null,
  hideHeader = false,
}) => {
  const body = <WidgetBody items={items} isLoading={isLoading} error={error} />;

  if (hideHeader) {
    return body;
  }

  return (
    <GlassCard title="Документы ЭДО (СБИС)" className="w-full">
      {body}
    </GlassCard>
  );
};

export default EdoWidget;