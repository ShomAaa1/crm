import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  listOrders,
  ORDER_STATUS_COLOR,
  ORDER_STATUS_LABEL,
} from "@/api/orders";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { OrderListItem, OrderStatus } from "@/types";

export function OrdersListPage() {
  const user = useAuthStore((s) => s.user);
  const isClient = user?.role === "client";

  const [items, setItems] = useState<OrderListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">("");
  const [error, setError] = useState<string | null>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const page = await listOrders({
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
        {isClient ? "Мои заказы" : "Заказы"}
      </h2>

      <div className="card p-3 flex items-end gap-3">
        <div>
          <label className="label">Статус</label>
          <select
            value={statusFilter}
            onChange={(e) =>
              setStatusFilter(e.target.value as OrderStatus | "")
            }
            className="input"
          >
            <option value="">Все</option>
            <option value="created">Созданы</option>
            <option value="confirmed">Подтверждены</option>
            <option value="shipped">Отгружены</option>
            <option value="delivered">Доставлены</option>
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
              {!isClient && (
                <th className="text-left px-4 py-2">Клиент</th>
              )}
              <th className="text-left px-4 py-2">Статус</th>
              <th className="text-center px-4 py-2">Позиций</th>
              <th className="text-right px-4 py-2">Сумма</th>
              <th className="text-left px-4 py-2">Трек-номер</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td
                  colSpan={isClient ? 6 : 7}
                  className="px-4 py-6 text-center text-slate-500"
                >
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td
                  colSpan={isClient ? 6 : 7}
                  className="px-4 py-6 text-center text-slate-500"
                >
                  Заказов нет
                </td>
              </tr>
            )}
            {!loading &&
              items.map((o) => (
                <tr key={o.id} className="border-t border-slate-100">
                  <td className="px-4 py-2 font-mono text-xs">
                    <Link
                      to={`/orders/${o.id}`}
                      className="text-brand-700 hover:underline"
                    >
                      {o.order_number}
                    </Link>
                  </td>
                  <td className="px-4 py-2 text-slate-600">
                    {new Date(o.created_at).toLocaleDateString("ru-RU")}
                  </td>
                  {!isClient && (
                    <td className="px-4 py-2">{o.client_company || "—"}</td>
                  )}
                  <td className="px-4 py-2">
                    <span
                      className={`px-2 py-0.5 rounded text-xs ${ORDER_STATUS_COLOR[o.status]}`}
                    >
                      {ORDER_STATUS_LABEL[o.status]}
                    </span>
                  </td>
                  <td className="px-4 py-2 text-center">{o.items_count}</td>
                  <td className="px-4 py-2 text-right font-medium">
                    {o.total_amount} ₽
                  </td>
                  <td className="px-4 py-2 text-slate-600 font-mono text-xs">
                    {o.tracking_number || "—"}
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
