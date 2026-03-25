const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "/api").replace(/\/+$/, "");

export const AUTH_STORAGE_KEY = "vikki_access_token";
export const UNAUTHORIZED_EVENT = "vikki:unauthorized";

export class AuthError extends Error {
  constructor(status, message, payload = null) {
    super(message);
    this.name = "AuthError";
    this.status = status;
    this.payload = payload;
  }
}

const createUrl = (path) => {
  return new URL(`${API_BASE_URL}${path}`, window.location.origin).toString();
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
    if (payload.detail) return payload.detail;
    if (Array.isArray(payload.detail) && payload.detail[0]?.msg) {
      return payload.detail[0].msg;
    }
    if (payload.message) return payload.message;
    if (payload.error) return payload.error;
  }

  if (status === 401) return "Неверный логин или пароль.";
  if (status === 403) return "Недостаточно прав доступа.";
  if (status === 404) return "Ресурс не найден.";

  return "Ошибка авторизации.";
};

export const getStoredToken = () => window.localStorage.getItem(AUTH_STORAGE_KEY);

export const setStoredToken = (token) => {
  window.localStorage.setItem(AUTH_STORAGE_KEY, token);
};

export const clearStoredToken = () => {
  window.localStorage.removeItem(AUTH_STORAGE_KEY);
};

export async function login(email, password, tenantSlug) {
  const response = await fetch(createUrl("/auth/login"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    body: JSON.stringify({
      email,
      password,
      tenant_slug: tenantSlug,
    }),
  });

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    throw new AuthError(
      response.status,
      extractErrorMessage(response.status, payload),
      payload
    );
  }

  if (!payload?.access_token) {
    throw new AuthError(500, "Login не вернул access_token.", payload);
  }

  setStoredToken(payload.access_token);
  return payload;
}

export async function fetchCurrentUser() {
  const token = getStoredToken();

  if (!token) {
    throw new AuthError(401, "Нет активной сессии.");
  }

  const response = await fetch(createUrl("/auth/me"), {
    method: "GET",
    headers: {
      Accept: "application/json",
      Authorization: `Bearer ${token}`,
    },
  });

  const payload = await parseResponseBody(response);

  if (!response.ok) {
    clearStoredToken();
    window.dispatchEvent(new CustomEvent(UNAUTHORIZED_EVENT));

    throw new AuthError(
      response.status,
      extractErrorMessage(response.status, payload),
      payload
    );
  }

  return payload;
}