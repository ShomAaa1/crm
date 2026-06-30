import { useEffect, useState } from "react";
import {
  listAvailableManagers,
  type ManagerAvailability,
} from "@/api/managers";
import { extractError } from "@/api/client";

interface Props {
  currentManagerId: string | null;
  onCancel: () => void;
  onSubmit: (managerId: string, reason: string) => Promise<void>;
}

const HEAVY_LOAD_THRESHOLD = 5;

export function AssignManagerModal({
  currentManagerId,
  onCancel,
  onSubmit,
}: Props) {
  const [managers, setManagers] = useState<ManagerAvailability[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    listAvailableManagers()
      .then(setManagers)
      .catch((e) => setError(extractError(e)));
  }, []);

  async function handleSubmit() {
    if (!selectedId) return;
    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(selectedId, reason.trim());
    } catch (e) {
      setError(extractError(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 bg-slate-900/40 flex items-center justify-center z-50 p-4"
      onClick={onCancel}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="px-5 py-4 border-b border-slate-200">
          <h3 className="text-lg font-semibold">
            {currentManagerId ? "Переназначить менеджера" : "Назначить менеджера"}
          </h3>
          <p className="text-xs text-slate-500 mt-1">
            Выберите менеджера для ответственности за эту заявку
          </p>
        </div>

        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2">
          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}
          {managers === null && !error && (
            <div className="text-slate-500 text-sm py-4">Загрузка…</div>
          )}
          {managers?.length === 0 && (
            <div className="text-slate-400 text-sm py-4 text-center">
              Нет доступных менеджеров
            </div>
          )}
          {managers?.map((m) => {
            const isSelected = selectedId === m.id;
            const isCurrent = currentManagerId === m.id;
            const isDisabled = !m.is_available || isCurrent;
            const status = getLoadStatus(m);
            return (
              <button
                key={m.id}
                disabled={isDisabled}
                onClick={() => setSelectedId(m.id)}
                className={`w-full text-left p-3 rounded-md border transition-colors ${
                  isSelected
                    ? "border-brand-500 bg-brand-50/50"
                    : isDisabled
                      ? "border-slate-200 bg-slate-50 opacity-60 cursor-not-allowed"
                      : "border-slate-200 hover:border-brand-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="font-medium text-slate-800 flex items-center gap-2">
                      {m.full_name}
                      {isCurrent && (
                        <span className="text-xs font-normal text-slate-500 px-1.5 py-0.5 bg-slate-100 rounded">
                          текущий
                        </span>
                      )}
                    </div>
                    {m.specialization && (
                      <div className="text-xs text-slate-500 mt-0.5">
                        {m.specialization}
                        {m.department && ` · ${m.department}`}
                      </div>
                    )}
                  </div>
                  <div className="text-right text-xs whitespace-nowrap shrink-0">
                    <div className={status.color}>{status.label}</div>
                    <div className="text-slate-400 mt-0.5">
                      {m.active_requests_count} активных
                    </div>
                  </div>
                </div>
              </button>
            );
          })}
        </div>

        <div className="px-5 pt-3 pb-4 border-t border-slate-200 space-y-3">
          <div>
            <label className="text-xs text-slate-500 mb-1 block">
              Причина (опционально)
            </label>
            <input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Например, постоянный клиент"
              maxLength={500}
              className="input w-full"
            />
          </div>
          <div className="flex justify-end gap-2">
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
              disabled={!selectedId || submitting}
              className="btn-primary"
            >
              {submitting
                ? "Сохраняем…"
                : currentManagerId
                  ? "Переназначить"
                  : "Назначить"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function getLoadStatus(m: ManagerAvailability): {
  label: string;
  color: string;
} {
  if (!m.is_available) {
    return { label: "🔴 недоступен", color: "text-red-600" };
  }
  if (m.active_requests_count >= HEAVY_LOAD_THRESHOLD) {
    return { label: "🟡 загружен", color: "text-amber-600" };
  }
  return { label: "🟢 свободен", color: "text-emerald-600" };
}
