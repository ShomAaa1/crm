import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { listRequests, STATUS_COLOR, STATUS_LABEL } from "@/api/requests";
import { extractError } from "@/api/client";
import type { RequestListItem } from "@/types";

export function MyRequestsPage() {
  const [items, setItems] = useState<RequestListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const page = await listRequests({ limit: 100 });
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
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Мои заявки</h2>
        <Link to="/catalog" className="btn-secondary">
          В каталог
        </Link>
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
              <th className="text-left px-4 py-2">Статус</th>
              <th className="text-center px-4 py-2">Позиций</th>
              <th className="text-right px-4 py-2">Сумма</th>
              <th className="text-left px-4 py-2">Менеджер</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  Заявок пока нет.{" "}
                  <Link to="/catalog" className="text-brand-700 hover:underline">
                    Выбрать запчасти →
                  </Link>
                </td>
              </tr>
            )}
            {!loading &&
              items.map((r) => (
                <tr
                  key={r.id}
                  className="border-t border-slate-100 hover:bg-slate-50 cursor-pointer"
                >
                  <td className="px-4 py-2 font-mono text-xs">
                    <Link
                      to={`/requests/${r.id}`}
                      className="text-brand-700 hover:underline"
                    >
                      {r.request_number}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {new Date(r.created_at).toLocaleString("ru-RU")}
                  </td>
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${STATUS_COLOR[r.status]}`}
                    >
                      {STATUS_LABEL[r.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">{r.items_count}</td>
                  <td className="px-4 py-2 text-right font-medium">{r.total} ₽</td>
                  <td className="px-4 py-2 text-slate-600">
                    {r.manager_name || <span className="text-slate-400">—</span>}
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
