import { api } from "./client";
import type { NotificationItem, NotificationSummary } from "@/types";

export async function getNotifications(
  onlyUnread = false,
  limit = 20,
): Promise<NotificationSummary> {
  const { data } = await api.get<NotificationSummary>("/notifications", {
    params: { only_unread: onlyUnread, limit },
  });
  return data;
}

export async function markRead(id: string): Promise<NotificationItem> {
  const { data } = await api.post<NotificationItem>(`/notifications/${id}/read`);
  return data;
}

export async function markAllRead(): Promise<number> {
  const { data } = await api.post<{ marked: number }>("/notifications/read-all");
  return data.marked;
}

export function relatedLink(n: NotificationItem): string | null {
  if (!n.related_entity_id) return null;
  switch (n.related_entity_type) {
    case "request":
      return `/requests/${n.related_entity_id}`;
    case "cp":
      return `/proposals/${n.related_entity_id}`;
    case "order":
      return `/orders/${n.related_entity_id}`;
    default:
      return null;
  }
}
