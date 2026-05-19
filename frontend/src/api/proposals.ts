import { api } from "./client";
import type { CPDetail, CPListItem, CPStatus, Page } from "@/types";

export interface CPItemUpdate {
  id: string;
  quantity: number;
  unit_price: string;
  discount_percent: string;
}

export interface CPDraftUpdateInput {
  items?: CPItemUpdate[];
  items_to_remove?: string[];
  payment_terms?: string | null;
  delivery_terms?: string | null;
  valid_until?: string | null;
}

export interface ListParams {
  status?: CPStatus;
  limit?: number;
  offset?: number;
}

export async function listProposals(
  params: ListParams = {},
): Promise<Page<CPListItem>> {
  const { data } = await api.get<Page<CPListItem>>("/proposals", { params });
  return data;
}

export async function getProposal(id: string): Promise<CPDetail> {
  const { data } = await api.get<CPDetail>(`/proposals/${id}`);
  return data;
}

export async function getProposalByRequest(
  requestId: string,
): Promise<CPDetail | null> {
  const { data } = await api.get<CPDetail | null>(
    `/proposals/by-request/${requestId}`,
  );
  return data;
}

export async function createFromRequest(requestId: string): Promise<CPDetail> {
  const { data } = await api.post<CPDetail>(
    `/proposals/from-request/${requestId}`,
  );
  return data;
}

export async function updateProposal(
  id: string,
  payload: CPDraftUpdateInput,
): Promise<CPDetail> {
  const { data } = await api.patch<CPDetail>(`/proposals/${id}`, payload);
  return data;
}

export async function sendProposal(id: string): Promise<CPDetail> {
  const { data } = await api.post<CPDetail>(`/proposals/${id}/send`);
  return data;
}

export async function acceptProposal(id: string): Promise<CPDetail> {
  const { data } = await api.post<CPDetail>(`/proposals/${id}/accept`);
  return data;
}

export async function rejectProposal(
  id: string,
  reason?: string,
): Promise<CPDetail> {
  const { data } = await api.post<CPDetail>(`/proposals/${id}/reject`, { reason });
  return data;
}

export async function requestRevision(id: string): Promise<CPDetail> {
  const { data } = await api.post<CPDetail>(`/proposals/${id}/revision`);
  return data;
}

export const CP_STATUS_LABEL: Record<CPStatus, string> = {
  draft: "Черновик",
  sent: "Отправлено клиенту",
  accepted: "Принято",
  rejected: "Отклонено",
  expired: "Истекло",
};

export const CP_STATUS_COLOR: Record<CPStatus, string> = {
  draft: "bg-slate-100 text-slate-700",
  sent: "bg-purple-100 text-purple-800",
  accepted: "bg-green-100 text-green-800",
  rejected: "bg-red-100 text-red-800",
  expired: "bg-amber-100 text-amber-800",
};
