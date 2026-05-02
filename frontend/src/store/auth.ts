import { create } from "zustand";
import * as authApi from "@/api/auth";
import { tokens } from "@/api/client";
import type { User } from "@/types";

interface AuthState {
  user: User | null;
  loading: boolean;
  initialized: boolean;
  init: () => Promise<void>;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  loading: false,
  initialized: false,

  async init() {
    if (!tokens.access) {
      set({ initialized: true });
      return;
    }
    try {
      const user = await authApi.me();
      set({ user, initialized: true });
    } catch {
      tokens.clear();
      set({ user: null, initialized: true });
    }
  },

  async login(email, password) {
    set({ loading: true });
    try {
      const pair = await authApi.login(email, password);
      tokens.set(pair.access_token, pair.refresh_token);
      set({ user: pair.user });
    } finally {
      set({ loading: false });
    }
  },

  async logout() {
    const rt = tokens.refresh;
    if (rt) {
      try {
        await authApi.logout(rt);
      } catch {
        // ignore — всё равно чистим локально
      }
    }
    tokens.clear();
    set({ user: null });
  },
}));
