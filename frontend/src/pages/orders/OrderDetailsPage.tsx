import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  changeStatus,
  getOrder,
  ORDER_ALLOWED,
  ORDER_STATUS_COLOR,
  ORDER_STATUS_LABEL,
  updateOrder,
} from "@/api/orders";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { OrderDetail } from "@/types";

export function OrderDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const isManagerSide =
    user?.role === "manager" || user?.role === "head" || user?.role === "admin";

  const [data, setData] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [editing, setEditing] = useState(false);
  const [addrDraft, setAddrDraft] = useState("");
  const [trackDraft, setTrackDraft] = useState("");
  const [paymentDraft, setPaymentDraft] = useState("");

  async function load() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const o = await getOrder(id);
      setData(o);
      setAddrDraft(o.delivery_address ?? "");
      setTrackDraft(o.tracking_number ?? "");
      setPaymentDraft(o.payment_terms ?? "");
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

  async function action(fn: () => Promise<OrderDetail>) {
    setBusy(true);
    setError(null);
    try {
      const o = await fn();
      setData(o);
      setAddrDraft(o.delivery_address ?? "");
      setTrackDraft(o.tracking_number ?? "");
      setPaymentDraft(o.payment_terms ?? "");
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!data) return;
    await action(() =>
      updateOrder(data.id, {
        delivery_address: addrDraft || null,
        tracking_number: trackDraft || null,
        payment_terms: paymentDraft || null,
      }),
    );
    setEditing(false);
  }

  if (loading || !data) {
    return <div className="text-slate-500">Загрузка…</div>;
  }

  const isClient = user?.role === "client";

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold">
            Заказ{" "}
            <span className="font-mono text-base">{data.order_number}</span>
          </h2>
          <div className="mt-1 flex items-center gap-2 flex-wrap text-sm">
            <span
              className={`px-2 py-0.5 rounded text-xs ${ORDER_STATUS_COLOR[data.status]}`}
            >
              {ORDER_STATUS_LABEL[data.status]}
            </span>
            {data.cp_number && (
              <span className="text-slate-500">
                По{" "}
                <Link
                  to={`/proposals/${data.cp_id}`}
                  className="text-brand-700 hover:underline font-mono"
                >
                  {data.cp_number}
                </Link>
              </span>
            )}
            <span className="text-slate-500">
              {new Date(data.created_at).toLocaleString("ru-RU")}
            </span>
          </div>
        </div>
        <Link to="/orders" className="btn-secondary">
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
          {data.delivered_at && (
            <>
              <div className="mt-3 text-sm font-medium text-slate-700 mb-1">
                Доставлено
              </div>
              <div className="text-sm text-slate-600">
                {new Date(data.delivered_at).toLocaleString("ru-RU")}
              </div>
            </>
          )}
        </div>

        <div className="card p-4 space-y-2">
          <div className="flex items-center justify-between">
            <div className="text-sm font-medium text-slate-700">
              Доставка и оплата
            </div>
            {isManagerSide && !editing && (
              <button
                onClick={() => setEditing(true)}
                className="text-xs text-brand-700 hover:underline"
              >
                Изменить
              </button>
            )}
          </div>

          {editing ? (
            <div className="space-y-2">
              <div>
                <label className="label">Адрес доставки</label>
                <textarea
                  rows={2}
                  value={addrDraft}
                  onChange={(e) => setAddrDraft(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Условия оплаты</label>
                <textarea
                  rows={2}
                  value={paymentDraft}
                  onChange={(e) => setPaymentDraft(e.target.value)}
                  className="input"
                />
              </div>
              <div>
                <label className="label">Трек-номер</label>
                <input
                  value={trackDraft}
                  onChange={(e) => setTrackDraft(e.target.value)}
                  className="input"
                />
              </div>
              <div className="flex gap-2 justify-end">
                <button
                  onClick={() => {
                    setEditing(false);
                    setAddrDraft(data.delivery_address ?? "");
                    setTrackDraft(data.tracking_number ?? "");
                    setPaymentDraft(data.payment_terms ?? "");
                  }}
                  className="btn-secondary"
                >
                  Отмена
                </button>
                <button onClick={saveEdit} disabled={busy} className="btn-primary">
                  Сохранить
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="text-xs text-slate-500">Адрес:</div>
              <div className="text-sm text-slate-700 whitespace-pre-wrap">
                {data.delivery_address || (
                  <span className="text-slate-400">не указан</span>
                )}
              </div>
              <div className="text-xs text-slate-500 mt-2">Оплата:</div>
              <div className="text-sm text-slate-700 whitespace-pre-wrap">
                {data.payment_terms || (
                  <span className="text-slate-400">не указана</span>
                )}
              </div>
              <div className="text-xs text-slate-500 mt-2">Трек-номер:</div>
              <div className="text-sm font-mono text-slate-700">
                {data.tracking_number || (
                  <span className="text-slate-400">не назначен</span>
                )}
              </div>
            </>
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
              <th className="text-center px-4 py-2">Кол-во</th>
              <th className="text-right px-4 py-2">Сумма</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-mono text-xs">
                  {it.article || "—"}
                </td>
                <td className="px-4 py-2">{it.name || "—"}</td>
                <td className="px-4 py-2 text-right">{it.unit_price} ₽</td>
                <td className="px-4 py-2 text-center">{it.quantity}</td>
                <td className="px-4 py-2 text-right font-medium">
                  {it.total_price} ₽
                </td>
              </tr>
            ))}
            <tr className="border-t border-slate-200 bg-slate-50">
              <td colSpan={4} className="px-4 py-2 text-right font-medium">
                Итого
              </td>
              <td className="px-4 py-2 text-right font-semibold">
                {data.total_amount} ₽
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {isManagerSide && ORDER_ALLOWED[data.status].length > 0 && (
        <div className="card p-4 flex flex-wrap gap-2">
          {ORDER_ALLOWED[data.status].map((s) => (
            <button
              key={s}
              disabled={busy}
              onClick={() => {
                if (confirm(`Перевести в «${ORDER_STATUS_LABEL[s]}»?`)) {
                  action(() => changeStatus(data.id, s));
                }
              }}
              className={s === "cancelled" ? "btn-danger" : "btn-primary"}
            >
              → {ORDER_STATUS_LABEL[s]}
            </button>
          ))}
        </div>
      )}

      {(isClient || ORDER_ALLOWED[data.status].length === 0) && (
        <div className="card p-4 text-sm text-slate-500">
          {data.status === "delivered"
            ? "Заказ доставлен. Спасибо за покупку!"
            : data.status === "cancelled"
              ? "Заказ отменён."
              : isClient
                ? "Менеджер обрабатывает ваш заказ. Когда он будет отгружен, появится трек-номер."
                : null}
        </div>
      )}
    </div>
  );
}
