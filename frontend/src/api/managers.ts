import { api } from "./client";

export interface ManagerAvailability {
  id: string;
  user_id: string;
  full_name: string;
  specialization: string | null;
  department: string | null;
  is_available: boolean;
  active_requests_count: number;
}

export async function listAvailableManagers(): Promise<ManagerAvailability[]> {
  const { data } = await api.get<ManagerAvailability[]>("/managers/available");
  return data;
}
