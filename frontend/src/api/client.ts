import axios, { AxiosError, AxiosInstance } from "axios";
import type { ProblemDetail, TokenPair } from "@/types";

const API_BASE = "/api/v1";

const TOKEN_KEY = "autodetail.access_token";
const REFRESH_KEY = "autodetail.refresh_token";

export const tokens = {
  get access(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  },
  get refresh(): string | null {
    return localStorage.getItem(REFRESH_KEY);
  },
  set(access: string, refresh: string): void {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.request.use((config) => {
  const token = tokens.access;
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let refreshPromise: Promise<string> | null = null;

async function refreshTokens(): Promise<string> {
  const rt = tokens.refresh;
  if (!rt) throw new Error("no refresh token");

  const { data } = await axios.post<TokenPair>(`${API_BASE}/auth/refresh`, {
    refresh_token: rt,
  });
  tokens.set(data.access_token, data.refresh_token);
  return data.access_token;
}

api.interceptors.response.use(
  (resp) => resp,
  async (error: AxiosError<ProblemDetail>) => {
    const original = error.config as
      | (typeof error.config & { _retry?: boolean })
      | undefined;

    const isAuthEndpoint = original?.url?.startsWith("/auth/");
    if (
      error.response?.status === 401 &&
      original &&
      !original._retry &&
      !isAuthEndpoint &&
      tokens.refresh
    ) {
      original._retry = true;
      try {
        refreshPromise = refreshPromise ?? refreshTokens();
        const newToken = await refreshPromise;
        refreshPromise = null;
        original.headers = original.headers ?? {};
        original.headers.Authorization = `Bearer ${newToken}`;
        return api(original);
      } catch (e) {
        refreshPromise = null;
        tokens.clear();
        if (typeof window !== "undefined") {
          window.location.href = "/login";
        }
        return Promise.reject(e);
      }
    }
    return Promise.reject(error);
  },
);

export function extractError(err: unknown): string {
  if (axios.isAxiosError<ProblemDetail>(err)) {
    const data = err.response?.data;
    if (data?.detail) return data.detail;
    if (data?.title) return data.title;
    return err.message;
  }
  return err instanceof Error ? err.message : "Неизвестная ошибка";
}
