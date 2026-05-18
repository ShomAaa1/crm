import { api } from "./client";
import type { Page, RequestDetail, RequestListItem, RequestStatus } from "@/types";

export interface ListParams {
  status?: RequestStatus;
  scope?: "mine" | "unassigned";
  limit?: number;
  offset?: number;
}

export async function listRequests(
  params: ListParams = {},
): Promise<Page<RequestListItem>> {
  const { data } = await api.get<Page<RequestListItem>>("/requests", { params });
  return data;
}

export async function getRequest(id: string): Promise<RequestDetail> {
  const { data } = await api.get<RequestDetail>(`/requests/${id}`);
  return data;
}

export async function createRequest(comment: string | null): Promise<RequestDetail> {
  const { data } = await api.post<RequestDetail>("/requests", { comment });
  return data;
}

export async function takeRequest(id: string): Promise<RequestDetail> {
  const { data } = await api.post<RequestDetail>(`/requests/${id}/take`);
  return data;
}

export async function changeStatus(
  id: string,
  status: RequestStatus,
  reason?: string,
): Promise<RequestDetail> {
  const { data } = await api.post<RequestDetail>(`/requests/${id}/status`, {
    status,
    reason,
  });
  return data;
}

export async function cancelRequest(id: string): Promise<RequestDetail> {
  const { data } = await api.post<RequestDetail>(`/requests/${id}/cancel`);
  return data;
}

export const STATUS_LABEL: Record<RequestStatus, string> = {
  new: "Новая",
  in_progress: "В работе",
  cp_sent: "КП отправлено",
  accepted: "Принято",
  rejected: "Отклонено",
  revision_needed: "Требуется доработка",
  closed_success: "Закрыта (успешно)",
  closed_fail: "Закрыта (неуспешно)",
  cancelled: "Отменена",
};

export const STATUS_COLOR: Record<RequestStatus, string> = {
  new: "bg-blue-100 text-blue-800",
  in_progress: "bg-amber-100 text-amber-800",
  cp_sent: "bg-purple-100 text-purple-800",
  accepted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  revision_needed: "bg-orange-100 text-orange-800",
  closed_success: "bg-emerald-100 text-emerald-800",
  closed_fail: "bg-slate-200 text-slate-700",
  cancelled: "bg-slate-100 text-slate-500",
};
