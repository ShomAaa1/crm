import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  CP_STATUS_COLOR,
  CP_STATUS_LABEL,
  listProposals,
} from "@/api/proposals";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { CPListItem, CPStatus } from "@/types";

export function ProposalsListPage() {
  const user = useAuthStore((s) => s.user);
  const isClient = user?.role === "client";

  const [items, setItems] = useState<CPListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<CPStatus | "">("");
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const page = await listProposals({
        limit: 100,
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
  }, [statusFilter]);

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">
        {isClient ? "Мои КП" : "Коммерческие предложения"}
      </h2>

      <div className="card p-3 flex items-end gap-3">
        <div>
          <label className="label">Статус</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value as CPStatus | "")}
            className="input"
          >
            <option value="">Все</option>
            {!isClient && <option value="draft">Черновики</option>}
            <option value="sent">Отправлены</option>
            <option value="accepted">Приняты</option>
            <option value="rejected">Отклонены</option>
            <option value="expired">Истекли</option>
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
              <th className="text-left px-4 py-2">№ КП</th>
              <th className="text-left px-4 py-2">№ Заявки</th>
              {!isClient && (
                <th className="text-left px-4 py-2">Клиент</th>
              )}
              <th className="text-left px-4 py-2">Статус</th>
              <th className="text-right px-4 py-2">Сумма</th>
              <th className="text-left px-4 py-2">Действительно до</th>
              <th className="text-left px-4 py-2">Дата</th>
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
                  КП не найдены
                </td>
              </tr>
            )}
            {!loading &&
              items.map((cp) => (
                <tr key={cp.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-mono text-xs">
                    <Link
                      to={`/proposals/${cp.id}`}
                      className="text-brand-700 hover:underline"
                    >
                      {cp.cp_number}
                      {cp.version > 1 && ` (v${cp.version})`}
                    </Link>
                  </td>
                  <td className="px-4 py-2 font-mono text-xs">
                    {cp.request_number}
                  </td>
                  {!isClient && (
                    <td className="px-4 py-2">{cp.client_company || "—"}</td>
                  )}
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${CP_STATUS_COLOR[cp.status]}`}
                    >
                      {CP_STATUS_LABEL[cp.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-right font-medium">
                    {cp.total_amount ?? "—"} ₽
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {cp.valid_until || "—"}
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {new Date(cp.created_at).toLocaleDateString("ru-RU")}
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
