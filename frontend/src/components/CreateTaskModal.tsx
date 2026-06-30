import { useEffect, useState } from "react";
import {
  listAvailableManagers,
  type ManagerAvailability,
} from "@/api/managers";
import { createTask, type TaskPriority } from "@/api/tasks";
import { extractError } from "@/api/client";

interface Props {
  presetManagerId?: string;
  presetManagerName?: string;
  onCancel: () => void;
  onCreated: () => void;
}

const PRIORITIES: { value: TaskPriority; label: string }[] = [
  { value: "low", label: "Низкий" },
  { value: "medium", label: "Средний" },
  { value: "high", label: "Высокий" },
  { value: "critical", label: "Критический" },
];

export function CreateTaskModal({
  presetManagerId,
  presetManagerName,
  onCancel,
  onCreated,
}: Props) {
  const [managers, setManagers] = useState<ManagerAvailability[] | null>(null);
  const [managerId, setManagerId] = useState<string>(presetManagerId ?? "");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState<TaskPriority>("medium");
  const [dueDate, setDueDate] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (presetManagerId) return; // если задан — список не нужен
    listAvailableManagers()
      .then(setManagers)
      .catch((e) => setError(extractError(e)));
  }, [presetManagerId]);

  async function handleSubmit() {
    if (!managerId || !title.trim()) return;
    setSubmitting(true);
    setError(null);
    try {
      await createTask({
        manager_id: managerId,
        title: title.trim(),
        description: description.trim() || undefined,
        priority,
        due_date: dueDate || undefined,
      });
      onCreated();
    } catch (e) {
      setError(extractError(e));
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50 p-4"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold">Поставить задачу</h3>
          <p className="text-xs text-slate-500 mt-1">
            Корректирующее действие для менеджера (UC-10)
          </p>
        </div>

        <div className="px-5 py-4 space-y-3 max-h-[70vh] overflow-y-auto">
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Менеджер *
            </label>
            {presetManagerId ? (
              <div className="input bg-slate-50 cursor-not-allowed">
                {presetManagerName || "—"}
              </div>
            ) : (
              <select
                value={managerId}
                onChange={(e) => setManagerId(e.target.value)}
                className="input w-full"
                disabled={managers === null}
              >
                <option value="">— Выберите менеджера —</option>
                {managers?.map((m) => (
                  <option
                    key={m.id}
                    value={m.id}
                    disabled={!m.is_available}
                  >
                    {m.full_name}
                    {m.specialization && ` (${m.specialization})`}
                    {!m.is_available && " — недоступен"}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Название задачи *
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Например, прозвонить 5 просроченных клиентов"
              maxLength={255}
              className="input w-full"
            />
          </div>

          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Описание (опционально)
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Детали, контекст, критерии выполнения"
              rows={3}
              maxLength={2000}
              className="input w-full resize-none"
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Приоритет
              </label>
              <select
                value={priority}
                onChange={(e) => setPriority(e.target.value as TaskPriority)}
                className="input w-full"
              >
                {PRIORITIES.map((p) => (
                  <option key={p.value} value={p.value}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-xs text-slate-500 mb-1 block">
                Срок выполнения
              </label>
              <input
                type="date"
                value={dueDate}
                onChange={(e) => setDueDate(e.target.value)}
                className="input w-full"
              />
            </div>
          </div>
        </div>

        <div className="px-5 py-3 border-t border-slate-200 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={submitting}
            className="btn-secondary"
          >
            Отмена
          </button>
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!managerId || !title.trim() || submitting}
            className="btn-primary"
          >
            {submitting ? "Создаём…" : "Поставить задачу"}
          </button>
        </div>
      </div>
    </div>
  );
}
