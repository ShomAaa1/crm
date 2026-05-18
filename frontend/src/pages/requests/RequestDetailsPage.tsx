import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  cancelRequest,
  changeStatus,
  getRequest,
  STATUS_COLOR,
  STATUS_LABEL,
  takeRequest,
} from "@/api/requests";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { RequestDetail, RequestStatus } from "@/types";

// Допустимые переходы — должны совпадать с ALLOWED_TRANSITIONS на бэкенде
const ALLOWED: Record<RequestStatus, RequestStatus[]> = {
  new: ["in_progress", "cancelled"],
  in_progress: ["cp_sent", "revision_needed", "closed_fail"],
  cp_sent: ["accepted", "rejected", "revision_needed"],
  accepted: ["closed_success"],
  rejected: ["closed_fail"],
  revision_needed: ["in_progress", "closed_fail"],
  closed_success: [],
  closed_fail: [],
  cancelled: [],
};

export function RequestDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);

  const [data, setData] = useState<RequestDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function load() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const r = await getRequest(id);
      setData(r);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function action(fn: () => Promise<RequestDetail>) {
    setBusy(true);
    setError(null);
    try {
      const r = await fn();
      setData(r);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !data) {
    return <div className="text-slate-500">Загрузка…</div>;
  }

  const isClient = user?.role === "client";
  const isManagerSide =
    user?.role === "manager" || user?.role === "head" || user?.role === "admin";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold">
            Заявка{" "}
            <span className="font-mono text-base text-slate-700">
              {data.request_number}
            </span>
          </h2>
          <div className="mt-1 flex items-center gap-2 flex-wrap text-sm">
            <span
              className={`px-2 py-0.5 rounded text-xs ${STATUS_COLOR[data.status]}`}
            >
              {STATUS_LABEL[data.status]}
            </span>
            {data.sla_overdue && (
              <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">
                SLA просрочен
              </span>
            )}
            <span className="text-slate-500">
              {new Date(data.created_at).toLocaleString("ru-RU")}
            </span>
          </div>
        </div>
        <Link
          to={isClient ? "/requests" : "/manager/requests"}
          className="btn-secondary"
        >
          ← К списку
        </Link>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="text-sm font-medium text-slate-700 mb-2">Клиент</div>
          <div className="text-sm text-slate-600">
            {data.client_company || "—"}
          </div>
          <div className="mt-3 text-sm font-medium text-slate-700 mb-1">
            Менеджер
          </div>
          <div className="text-sm text-slate-600">
            {data.manager_name || (
              <span className="text-slate-400">не назначен</span>
            )}
          </div>
        </div>
        <div className="card p-4">
          <div className="text-sm font-medium text-slate-700 mb-2">
            Комментарий клиента
          </div>
          <div className="text-sm text-slate-600 whitespace-pre-wrap">
            {data.comment || <span className="text-slate-400">пусто</span>}
          </div>
          {data.sla_deadline && (
            <div className="mt-3 text-xs text-slate-500">
              SLA до:{" "}
              {new Date(data.sla_deadline).toLocaleString("ru-RU")}
            </div>
          )}
        </div>
      </div>

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">Артикул</th>
              <th className="text-left px-4 py-2">Название</th>
              <th className="text-right px-4 py-2">Цена</th>
              <th className="text-center px-4 py-2">Количество</th>
              <th className="text-right px-4 py-2">Сумма</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-mono text-xs">
                  {it.article || "—"}
                </td>
                <td className="px-4 py-2">{it.name || it.description}</td>
                <td className="px-4 py-2 text-right">
                  {it.price_at_moment ? `${it.price_at_moment} ₽` : "—"}
                </td>
                <td className="px-4 py-2 text-center">{it.quantity}</td>
                <td className="px-4 py-2 text-right font-medium">
                  {it.line_total ? `${it.line_total} ₽` : "—"}
                </td>
              </tr>
            ))}
            <tr className="border-t border-slate-200 bg-slate-50">
              <td colSpan={4} className="px-4 py-2 text-right font-medium">
                Итого
              </td>
              <td className="px-4 py-2 text-right font-semibold">
                {data.total} ₽
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className="card p-4 flex flex-wrap gap-2">
        {/* Действия клиента */}
        {isClient && data.status === "new" && (
          <button
            disabled={busy}
            onClick={() => action(() => cancelRequest(data.id))}
            className="btn-danger"
          >
            Отменить заявку
          </button>
        )}

        {/* Действия менеджера */}
        {isManagerSide && data.status === "new" && !data.manager_id && (
          <button
            disabled={busy}
            onClick={() => action(() => takeRequest(data.id))}
            className="btn-primary"
          >
            Взять в работу
          </button>
        )}

        {isManagerSide &&
          ALLOWED[data.status].length > 0 &&
          data.status !== "new" && (
            <StatusActions
              status={data.status}
              disabled={busy}
              onChange={(s) => action(() => changeStatus(data.id, s))}
            />
          )}

        {(!isClient && data.status === "new" && data.manager_id) ||
        (!ALLOWED[data.status].length && !isClient) ? null : null}

        {(data.status === "closed_success" ||
          data.status === "closed_fail" ||
          data.status === "cancelled") && (
          <span className="text-sm text-slate-500 self-center">
            Заявка закрыта{" "}
            {data.closed_at &&
              `(${new Date(data.closed_at).toLocaleString("ru-RU")})`}
          </span>
        )}
      </div>
    </div>
  );
}

function StatusActions({
  status,
  disabled,
  onChange,
}: {
  status: RequestStatus;
  disabled: boolean;
  onChange: (s: RequestStatus) => void;
}) {
  return (
    <>
      {ALLOWED[status].map((s) => (
        <button
          key={s}
          disabled={disabled}
          onClick={() => {
            if (confirm(`Перевести в статус «${STATUS_LABEL[s]}»?`)) {
              onChange(s);
            }
          }}
          className={
            s.startsWith("closed") || s === "rejected"
              ? "btn-secondary"
              : "btn-primary"
          }
        >
          → {STATUS_LABEL[s]}
        </button>
      ))}
    </>
  );
}
