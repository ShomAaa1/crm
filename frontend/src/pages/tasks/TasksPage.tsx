import { useEffect, useState } from "react";
import {
  completeTask,
  listTasks,
  PRIORITY_COLOR,
  PRIORITY_LABEL,
  STATUS_COLOR,
  STATUS_LABEL,
  type TaskOut,
  type TaskStatus,
} from "@/api/tasks";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { CreateTaskModal } from "@/components/CreateTaskModal";

const STATUS_FILTERS: { value: TaskStatus | "all" | "active"; label: string }[] =
  [
    { value: "active", label: "Активные" },
    { value: "all", label: "Все" },
    { value: "completed", label: "Выполненные" },
    { value: "cancelled", label: "Отменённые" },
  ];

export function TasksPage() {
  const user = useAuthStore((s) => s.user);
  const isManager = user?.role === "manager";
  const isHeadOrAdmin = user?.role === "head" || user?.role === "admin";

  const [tasks, setTasks] = useState<TaskOut[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TaskStatus | "all" | "active">("active");
  const [showCreate, setShowCreate] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const list = await listTasks();
      let filtered = list;
      if (filter === "active") {
        filtered = list.filter(
          (t) => t.status === "pending" || t.status === "in_progress",
        );
      } else if (filter !== "all") {
        filtered = list.filter((t) => t.status === filter);
      }
      // Сортировка: просроченные первыми, затем по приоритету, затем по дате
      const priorityWeight: Record<string, number> = {
        critical: 0,
        high: 1,
        medium: 2,
        low: 3,
      };
      filtered.sort((a, b) => {
        if (a.is_overdue !== b.is_overdue) return a.is_overdue ? -1 : 1;
        const pa = priorityWeight[a.priority] ?? 9;
        const pb = priorityWeight[b.priority] ?? 9;
        if (pa !== pb) return pa - pb;
        return a.created_at < b.created_at ? 1 : -1;
      });
      setTasks(filtered);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  async function handleComplete(id: string) {
    try {
      await completeTask(id);
      await reload();
    } catch (e) {
      alert(extractError(e));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">
          {isManager ? "Мои задачи" : "Задачи отдела"}
        </h2>
        {isHeadOrAdmin && (
          <button
            onClick={() => setShowCreate(true)}
            className="btn-primary"
          >
            + Поставить задачу
          </button>
        )}
      </div>

      <div className="card p-3 flex gap-1">
        {STATUS_FILTERS.map((f) => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 rounded text-sm ${
              filter === f.value
                ? "bg-brand-600 text-white"
                : "bg-slate-100 text-slate-700 hover:bg-slate-200"
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <div className="text-slate-500">Загрузка…</div>}

      {!loading && tasks.length === 0 && (
        <div className="card p-8 text-center text-slate-400">
          Задач нет
        </div>
      )}

      <div className="space-y-3">
        {tasks.map((t) => (
          <TaskCard
            key={t.id}
            task={t}
            showManager={!isManager}
            showAssignedBy={isManager}
            onComplete={isManager ? () => handleComplete(t.id) : undefined}
          />
        ))}
      </div>

      {showCreate && (
        <CreateTaskModal
          onCancel={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            reload();
          }}
        />
      )}
    </div>
  );
}

function TaskCard({
  task,
  showManager,
  showAssignedBy,
  onComplete,
}: {
  task: TaskOut;
  showManager: boolean;
  showAssignedBy: boolean;
  onComplete?: () => void;
}) {
  const dueLabel = formatDue(task);
  const isActive = task.status === "pending" || task.status === "in_progress";

  return (
    <div
      className={`card p-4 ${
        task.is_overdue ? "border-red-300 bg-red-50/30" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <span
              className={`px-2 py-0.5 rounded text-xs ${PRIORITY_COLOR[task.priority]}`}
            >
              {PRIORITY_LABEL[task.priority]}
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs ${STATUS_COLOR[task.status]}`}
            >
              {STATUS_LABEL[task.status]}
            </span>
            {task.is_overdue && (
              <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">
                ⚠ Просрочена
              </span>
            )}
          </div>
          <div className="font-medium text-slate-800">{task.title}</div>
          {task.description && (
            <div className="mt-1 text-sm text-slate-600 whitespace-pre-wrap">
              {task.description}
            </div>
          )}
          <div className="mt-2 flex flex-wrap gap-3 text-xs text-slate-500">
            {showManager && task.manager_name && (
              <span>👤 {task.manager_name}</span>
            )}
            {showAssignedBy && task.assigned_by_name && (
              <span>от {task.assigned_by_name}</span>
            )}
            {dueLabel && <span>{dueLabel}</span>}
            {task.completed_at && (
              <span>
                ✓ Выполнено{" "}
                {new Date(task.completed_at).toLocaleString("ru-RU")}
              </span>
            )}
          </div>
        </div>
        {isActive && onComplete && (
          <button onClick={onComplete} className="btn-primary text-sm">
            Выполнено
          </button>
        )}
      </div>
    </div>
  );
}

function formatDue(t: TaskOut): string | null {
  if (!t.due_date) return null;
  const due = new Date(t.due_date);
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const diffDays = Math.round(
    (due.getTime() - today.getTime()) / (1000 * 60 * 60 * 24),
  );
  if (t.status === "completed" || t.status === "cancelled") {
    return `📅 ${t.due_date}`;
  }
  if (diffDays < 0) return `📅 Срок: ${t.due_date} (просрочено на ${-diffDays} дн.)`;
  if (diffDays === 0) return `📅 Срок: сегодня`;
  if (diffDays === 1) return `📅 Срок: завтра`;
  return `📅 Срок: через ${diffDays} дн. (${t.due_date})`;
}
