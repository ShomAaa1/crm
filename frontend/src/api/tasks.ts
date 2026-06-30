import { api } from "./client";

export type TaskPriority = "low" | "medium" | "high" | "critical";
export type TaskStatus = "pending" | "in_progress" | "completed" | "cancelled";

export interface TaskOut {
  id: string;
  manager_id: string;
  manager_name: string | null;
  assigned_by: string | null;
  assigned_by_name: string | null;
  title: string;
  description: string | null;
  priority: TaskPriority;
  status: TaskStatus;
  due_date: string | null;
  completed_at: string | null;
  created_at: string;
  is_overdue: boolean;
}

export interface TaskCreateIn {
  manager_id: string;
  title: string;
  description?: string;
  priority?: TaskPriority;
  due_date?: string; // YYYY-MM-DD
}

export interface TaskUpdateIn {
  title?: string;
  description?: string;
  priority?: TaskPriority;
  due_date?: string | null;
  status?: TaskStatus;
}

export async function listTasks(params?: {
  status?: TaskStatus;
  only_mine?: boolean;
}): Promise<TaskOut[]> {
  const { data } = await api.get<TaskOut[]>("/tasks", { params });
  return data;
}

export async function createTask(payload: TaskCreateIn): Promise<TaskOut> {
  const { data } = await api.post<TaskOut>("/tasks", payload);
  return data;
}

export async function updateTask(
  id: string,
  payload: TaskUpdateIn,
): Promise<TaskOut> {
  const { data } = await api.patch<TaskOut>(`/tasks/${id}`, payload);
  return data;
}

export async function completeTask(id: string): Promise<TaskOut> {
  const { data } = await api.post<TaskOut>(`/tasks/${id}/complete`);
  return data;
}

export const PRIORITY_LABEL: Record<TaskPriority, string> = {
  low: "Низкий",
  medium: "Средний",
  high: "Высокий",
  critical: "Критический",
};

export const PRIORITY_COLOR: Record<TaskPriority, string> = {
  low: "bg-slate-100 text-slate-700",
  medium: "bg-blue-100 text-blue-800",
  high: "bg-amber-100 text-amber-800",
  critical: "bg-red-100 text-red-800",
};

export const STATUS_LABEL: Record<TaskStatus, string> = {
  pending: "Ожидает",
  in_progress: "В работе",
  completed: "Выполнена",
  cancelled: "Отменена",
};

export const STATUS_COLOR: Record<TaskStatus, string> = {
  pending: "bg-slate-100 text-slate-700",
  in_progress: "bg-amber-100 text-amber-800",
  completed: "bg-emerald-100 text-emerald-800",
  cancelled: "bg-slate-100 text-slate-500",
};
