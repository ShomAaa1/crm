import { api } from "./client";
import type { OrderDetail, OrderListItem, OrderStatus, Page } from "@/types";

export interface ListParams {
  status?: OrderStatus;
  limit?: number;
  offset?: number;
}

export async function listOrders(
  params: ListParams = {},
): Promise<Page<OrderListItem>> {
  const { data } = await api.get<Page<OrderListItem>>("/orders", { params });
  return data;
}

export async function getOrder(id: string): Promise<OrderDetail> {
  const { data } = await api.get<OrderDetail>(`/orders/${id}`);
  return data;
}

export async function getOrderByCp(cpId: string): Promise<OrderDetail | null> {
  const { data } = await api.get<OrderDetail | null>(`/orders/by-cp/${cpId}`);
  return data;
}

export async function updateOrder(
  id: string,
  payload: {
    delivery_address?: string | null;
    payment_terms?: string | null;
    tracking_number?: string | null;
  },
): Promise<OrderDetail> {
  const { data } = await api.patch<OrderDetail>(`/orders/${id}`, payload);
  return data;
}

export async function changeStatus(
  id: string,
  status: OrderStatus,
  reason?: string,
): Promise<OrderDetail> {
  const { data } = await api.post<OrderDetail>(`/orders/${id}/status`, {
    status,
    reason,
  });
  return data;
}

export const ORDER_STATUS_LABEL: Record<OrderStatus, string> = {
  created: "Создан",
  confirmed: "Подтверждён",
  shipped: "Отгружен",
  delivered: "Доставлен",
  cancelled: "Отменён",
};

export const ORDER_STATUS_COLOR: Record<OrderStatus, string> = {
  created: "bg-slate-100 text-slate-700",
  confirmed: "bg-blue-100 text-blue-800",
  shipped: "bg-amber-100 text-amber-800",
  delivered: "bg-green-100 text-green-800",
  cancelled: "bg-red-100 text-red-800",
};

export const ORDER_ALLOWED: Record<OrderStatus, OrderStatus[]> = {
  created: ["confirmed", "cancelled"],
  confirmed: ["shipped", "cancelled"],
  shipped: ["delivered", "cancelled"],
  delivered: [],
  cancelled: [],
};
