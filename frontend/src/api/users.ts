import { api } from "./client";
import type { Page, User, UserRole } from "@/types";

export interface UserListParams {
  role?: UserRole;
  is_active?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export async function listUsers(params: UserListParams = {}): Promise<Page<User>> {
  const { data } = await api.get<Page<User>>("/users", { params });
  return data;
}

export interface UserCreateInput {
  email: string;
  password: string;
  role: UserRole;
  full_name: string;
  phone?: string | null;
}

export async function createUser(payload: UserCreateInput): Promise<User> {
  const { data } = await api.post<User>("/users", payload);
  return data;
}

export async function blockUser(id: string): Promise<void> {
  await api.post(`/users/${id}/block`);
}

export async function unblockUser(id: string): Promise<void> {
  await api.post(`/users/${id}/unblock`);
}
