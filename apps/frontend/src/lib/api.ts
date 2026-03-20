import { clearStoredToken, getStoredToken, UNAUTHORIZED_EVENT } from "./auth";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor(status, message, payload = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.payload = payload;
  }
}

const createUrl = (path, params = {}) => {
  const url = new URL(`${API_BASE_URL}${path}`, window.location.origin);

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === "") return;
    url.searchParams.set(key, String(value));
  });

  return url.toString();
};

const parseResponseBody = async (response) => {
  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    return response.json();
  }

  const text = await response.text();

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
};

const extractErrorMessage = (status, payload) => {
  if (typeof payload === "string" && payload.trim()) return payload;

  if (payload && typeof payload === "object") {
    if (payload.detail) {
      if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
        return payload.detail[0].msg;
      }
      return payload.detail;
    }
    if (payload.message) return payload.message;
    if (payload.error) return payload.error;
  }

  if (status === 401) return "Нет активной авторизации.";
  if (status === 403) return "Недостаточно прав для чтения данных.";
  if (status === 404) return "Ресурс не найден.";

  return "Ошибка API.";
};

async function apiRequest(method, path, params = {}, body = null) {
  const token = getStoredToken();

  const response = await fetch(createUrl(path, params), {
    method,
    headers: {
      Accept: "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(body ? { "Content-Type": "application/json" } : {}),
    },
    ...(body ? { body: JSON.stringify(body) } : {}),
  });

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    if (response.status === 401) {
      clearStoredToken();
      window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));
    }

    throw new ApiError(
      response.status,
      extractErrorMessage(response.status, payload),
      payload
    );
  }

  return payload;
}

export async function apiGet(path, params = {}) {
  return apiRequest("GET", path, params);
}

export const loadDashboard = (days = 7) => apiGet("/analytics/dashboard", { days });
export const loadTransactions = (params = {}) => apiGet("/transactions", params);
export const loadNotifications = (params = {}) => apiGet("/notifications", params);

export const formatCurrency = (value) =>
  new Intl.NumberFormat("ru-RU", {
    style: "currency",
    currency: "RUB",
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

export const formatCompactNumber = (value) =>
  new Intl.NumberFormat("ru-RU", {
    maximumFractionDigits: 0,
  }).format(Number(value || 0));

export const formatDateTime = (value) => {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ru-RU", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
};

export const formatDayLabel = (value) => {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("ru-RU", {
    weekday: "short",
  })
    .format(date)
    .replace(".", "")
    .toUpperCase();
};

export const formatRelativeLabel = (value) => {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;

  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60000);

  if (diffMinutes < 1) return "сейчас";
  if (diffMinutes < 60) return `${diffMinutes} мин назад`;

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) return `${diffHours} ч назад`;

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) return "вчера";
  if (diffDays < 7) return `${diffDays} дн назад`;

  return formatDateTime(value);
};

export const truncate = (value, max = 64) => {
  if (!value) return "—";
  return value.length > max ? `${value.slice(0, max - 1)}…` : value;
};

export const notificationTone = (type) => {
  switch ((type || "").toLowerCase()) {
    case "success":
      return "success";
    case "warning":
      return "warning";
    case "error":
      return "error";
    default:
      return "info";
  }
};

export const toSignedAmount = (amount, transactionType) => {
  const numeric = Number(amount || 0);
  const sign = transactionType === "incoming" ? "+" : "-";
  return `${sign}${formatCurrency(Math.abs(numeric))}`;
};