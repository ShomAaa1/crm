import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRequests, STATUS_COLOR, STATUS_LABEL } from "@/api/requests";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { RequestListItem, RequestStatus } from "@/types";

type Scope = "unassigned" | "mine" | "all";

const SCOPE_LABEL: Record<Scope, string> = {
  unassigned: "Без менеджера",
  mine: "Мои",
  all: "Все",
};

export function ManagerRequestsPage() {
  const user = useAuthStore((s) => s.user);
  const canSeeAll = user?.role === "head" || user?.role === "admin";

  const [scope, setScope] = useState<Scope>("unassigned");
  const [statusFilter, setStatusFilter] = useState<RequestStatus | "">("");
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (scope === "unassigned" || scope === "mine") params.scope = scope;
      if (statusFilter) params.status = statusFilter;
      const page = await listRequests({
        limit: 100,
        ...(scope !== "all" ? { scope: scope as "mine" | "unassigned" } : {}),
        ...(statusFilter ? { status: statusFilter } : {}),
      });
      setItems(page.items);
      setTotal(page.total);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scope, statusFilter]);

  // Менеджер: «Без менеджера / Мои» (видит только бесхозные и свои)
  // Руководитель/админ: «Без менеджера / Все» (всё видит, «Мои» не имеет смысла)
  const scopes: Scope[] = canSeeAll
    ? ["unassigned", "all"]
    : ["unassigned", "mine"];

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Заявки</h2>
        <Link
          to="/manager/requests/new"
          className="px-3 py-1.5 rounded bg-brand-600 text-white text-sm hover:bg-brand-700"
        >
          + Оформить заявку для клиента
        </Link>
      </div>

      <div className="card p-3 flex flex-wrap items-end gap-3">
        <div className="flex gap-1">
          {scopes.map((s) => (
            <button
              key={s}
              onClick={() => setScope(s)}
              className={`px-3 py-1.5 rounded text-sm ${
                scope === s
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {SCOPE_LABEL[s]}
            </button>
          ))}
        </div>
        <div className="ml-auto">
          <label className="label">Статус</label>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as RequestStatus | "")
            }
            className="input"
          >
            <option value="">Все</option>
            <option value="new">Новые</option>
            <option value="in_progress">В работе</option>
            <option value="cp_sent">КП отправлено</option>
            <option value="accepted">Приняты</option>
            <option value="rejected">Отклонены</option>
            <option value="revision_needed">Требуется доработка</option>
            <option value="closed_success">Закрыты (успех)</option>
            <option value="closed_fail">Закрыты (неуспех)</option>
            <option value="cancelled">Отменены</option>
          </select>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">№</th>
              <th className="text-left px-4 py-2">Дата</th>
              <th className="text-left px-4 py-2">Клиент</th>
              <th className="text-left px-4 py-2">Статус</th>
              <th className="text-center px-4 py-2">Позиций</th>
              <th className="text-right px-4 py-2">Сумма</th>
              <th className="text-left px-4 py-2">Менеджер</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-4 py-6 text-center text-slate-500">
                  Заявок не найдено
                </td>
              </tr>
            )}
            {!loading &&
              items.map((r) => (
                <tr
                  key={r.id}
                  className={`border-t border-slate-100 hover:bg-slate-50 ${
                    r.sla_overdue ? "bg-red-50/30" : ""
                  }`}
                >
                  <td className="px-4 py-2 font-mono text-xs">
                    <Link
                      to={`/requests/${r.id}`}
                      className="text-brand-700 hover:underline"
                    >
                      {r.request_number}
                    </Link>
                    {r.sla_overdue && (
                      <span className="ml-2 text-xs text-red-700">SLA!</span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {new Date(r.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td className="px-4 py-2">{r.client_company || "—"}</td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${STATUS_COLOR[r.status]}`}
                    >
                      {STATUS_LABEL[r.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">{r.items_count}</td>
                  <td className="px-4 py-2 text-right font-medium">
                    {r.total} ₽
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {r.manager_name || (
                      <span className="text-slate-400">не назначен</span>
                    )}
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-500">Всего: {total}</div>
    </div>
  );
}
