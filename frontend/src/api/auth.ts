import { api } from "./client";
import type { TokenPair, User } from "@/types";

export async function login(email: string, password: string): Promise<TokenPair> {
  const { data } = await api.post<TokenPair>("/auth/login", { email, password });
  return data;
}

export async function me(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

export async function logout(refresh_token: string): Promise<void> {
  await api.post("/auth/logout", { refresh_token });
}
