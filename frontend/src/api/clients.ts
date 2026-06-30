import { api } from "./client";

export interface ClientContactOut {
  id: string;
  full_name: string;
  position: string | null;
  phone: string | null;
  email: string | null;
  is_primary: boolean;
}

export interface ClientCard {
  id: string;
  company_name: string;
  inn: string;
  kpp: string | null;
  ogrn: string | null;
  legal_address: string | null;
  delivery_address: string | null;
  credit_limit: number;
  debt: number;
  assigned_manager_id: string | null;
  assigned_manager_name: string | null;
  contacts: ClientContactOut[];
}

export type ActivityKind =
  | "request_created"
  | "request_taken"
  | "request_status"
  | "cp_created"
  | "cp_sent"
  | "cp_accepted"
  | "cp_rejected"
  | "order_created"
  | "order_status";

export interface ActivityEvent {
  timestamp: string;
  kind: ActivityKind;
  title: string;
  description: string | null;
  entity_type: string;
  entity_id: string;
  entity_number: string | null;
  actor_name: string | null;
  amount: number | null;
}

export interface ClientListItem {
  id: string;
  company_name: string;
  inn: string;
  assigned_manager_id: string | null;
}

export async function listClients(search?: string): Promise<ClientListItem[]> {
  const { data } = await api.get<ClientListItem[]>("/clients", {
    params: search ? { search } : {},
  });
  return data;
}

export async function getClient(id: string): Promise<ClientCard> {
  const { data } = await api.get<ClientCard>(`/clients/${id}`);
  return data;
}

export interface InnCheck {
  exists: boolean;
  client_id: string | null;
  company_name: string | null;
}

export async function checkInn(inn: string): Promise<InnCheck> {
  const { data } = await api.get<InnCheck>("/clients/check-inn", {
    params: { inn },
  });
  return data;
}

export async function getClientActivity(
  id: string,
): Promise<ActivityEvent[]> {
  const { data } = await api.get<ActivityEvent[]>(`/clients/${id}/activity`);
  return data;
}

export const ACTIVITY_ICON: Record<ActivityKind, string> = {
  request_created: "📩",
  request_taken: "🔵",
  request_status: "🏁",
  cp_created: "📝",
  cp_sent: "📧",
  cp_accepted: "✅",
  cp_rejected: "❌",
  order_created: "📦",
  order_status: "🚚",
};
