import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  acceptProposal,
  createFromRequest,
  CP_STATUS_COLOR,
  CP_STATUS_LABEL,
  downloadProposalPdf,
  getProposal,
  rejectProposal,
  requestRevision,
  sendProposal,
  updateProposal,
  type CPItemUpdate,
} from "@/api/proposals";
import { getOrderByCp, ORDER_STATUS_LABEL } from "@/api/orders";
import { listParts } from "@/api/catalog";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { CPDetail, OrderDetail, Part } from "@/types";

export function ProposalDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);

  const [data, setData] = useState<CPDetail | null>(null);
  const [order, setOrder] = useState<OrderDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Локальные правки черновика
  const [draft, setDraft] = useState<CPItemUpdate[]>([]);
  const [removed, setRemoved] = useState<Set<string>>(new Set());
  const [paymentTerms, setPaymentTerms] = useState("");
  const [deliveryTerms, setDeliveryTerms] = useState("");

  // Добавление новой позиции в КП (ФТ-11)
  const [addSearch, setAddSearch] = useState("");
  const [addResults, setAddResults] = useState<Part[]>([]);
  const [addSearching, setAddSearching] = useState(false);

  async function load() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const cp = await getProposal(id);
      applyData(cp);
      try {
        const o = await getOrderByCp(cp.id);
        setOrder(o);
      } catch {
        setOrder(null);
      }
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  function applyData(cp: CPDetail) {
    setData(cp);
    setDraft(
      cp.items.map((i) => ({
        id: i.id,
        quantity: i.quantity,
        unit_price: i.unit_price,
        discount_percent: i.discount_percent,
      })),
    );
    setRemoved(new Set());
    setPaymentTerms(cp.payment_terms ?? "");
    setDeliveryTerms(cp.delivery_terms ?? "");
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const isClient = user?.role === "client";
  const isManagerSide =
    user?.role === "manager" || user?.role === "head" || user?.role === "admin";

  const isEditable = data?.status === "draft" && isManagerSide;
  const canAct = data?.status === "sent" && isClient;

  const liveTotal = useMemo(() => {
    if (!data) return "0.00";
    let t = 0;
    for (const it of data.items) {
      if (removed.has(it.id)) continue;
      const upd = draft.find((d) => d.id === it.id);
      const qty = upd?.quantity ?? it.quantity;
      const price = Number(upd?.unit_price ?? it.unit_price);
      const disc = Number(upd?.discount_percent ?? it.discount_percent);
      t += qty * price * (100 - disc) / 100;
    }
    return t.toFixed(2);
  }, [data, draft, removed]);

  async function saveDraft() {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      const updated = await updateProposal(data.id, {
        items: draft.filter((d) => !removed.has(d.id)),
        items_to_remove: removed.size > 0 ? Array.from(removed) : undefined,
        payment_terms: paymentTerms || null,
        delivery_terms: deliveryTerms || null,
      });
      applyData(updated);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  async function doAddSearch() {
    setAddSearching(true);
    setError(null);
    try {
      const page = await listParts({
        search: addSearch.trim() || undefined,
        is_active: true,
        limit: 10,
      });
      setAddResults(page.items);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setAddSearching(false);
    }
  }

  async function addPosition(partId: string) {
    if (!data) return;
    setBusy(true);
    setError(null);
    try {
      // Сохраняем текущие правки черновика вместе с новой позицией,
      // цена подставляется на бэкенде из каталога (snapshot).
      const updated = await updateProposal(data.id, {
        items: draft.filter((d) => !removed.has(d.id)),
        items_to_remove: removed.size > 0 ? Array.from(removed) : undefined,
        items_to_add: [{ part_id: partId, quantity: 1 }],
        payment_terms: paymentTerms || null,
        delivery_terms: deliveryTerms || null,
      });
      applyData(updated);
      setAddResults([]);
      setAddSearch("");
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  async function action(fn: () => Promise<CPDetail>) {
    setBusy(true);
    setError(null);
    try {
      const cp = await fn();
      applyData(cp);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="text-slate-500">Загрузка…</div>;
  if (!data)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
        {error || "Не удалось загрузить КП"}
      </div>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold">
            КП <span className="font-mono text-base">{data.cp_number}</span>
            {data.version > 1 && (
              <span className="ml-2 text-sm text-slate-500">
                v{data.version}
              </span>
            )}
          </h2>
          <div className="mt-1 flex items-center gap-2 flex-wrap text-sm">
            <span
              className={`px-2 py-0.5 rounded text-xs ${CP_STATUS_COLOR[data.status]}`}
            >
              {CP_STATUS_LABEL[data.status]}
            </span>
            <span className="text-slate-500">
              К заявке{" "}
              <Link
                to={`/requests/${data.request_id}`}
                className="text-brand-700 hover:underline font-mono"
              >
                {data.request_number}
              </Link>
            </span>
            {data.client_company && (
              <span className="text-slate-500">· {data.client_company}</span>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={() => downloadProposalPdf(data.id, data.cp_number)}
            className="btn-secondary"
          >
            📄 Скачать PDF
          </button>
          <Link
            to={isClient ? "/proposals" : "/manager/proposals"}
            className="btn-secondary"
          >
            ← К списку
          </Link>
        </div>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {order && (
        <div className="card p-4 flex items-center justify-between bg-green-50/50 border-green-200">
          <div>
            <div className="text-sm text-slate-600 mb-1">
              По принятому КП создан заказ
            </div>
            <div className="flex items-center gap-2">
              <Link
                to={`/orders/${order.id}`}
                className="font-mono text-brand-700 hover:underline"
              >
                {order.order_number}
              </Link>
              <span className="text-xs text-slate-500">·</span>
              <span className="text-sm">{ORDER_STATUS_LABEL[order.status]}</span>
              <span className="text-xs text-slate-500">·</span>
              <span className="text-sm font-medium">{order.total_amount} ₽</span>
            </div>
          </div>
          <Link to={`/orders/${order.id}`} className="btn-secondary">
            Открыть заказ →
          </Link>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">Артикул</th>
              <th className="text-left px-4 py-2">Название</th>
              <th className="text-center px-4 py-2 w-24">Кол-во</th>
              <th className="text-right px-4 py-2 w-32">Цена</th>
              <th className="text-center px-4 py-2 w-24">Скидка %</th>
              <th className="text-right px-4 py-2 w-32">Сумма</th>
              {isEditable && <th className="px-4 py-2 w-12"></th>}
            </tr>
          </thead>
          <tbody>
            {data.items.map((it) => {
              const isRemoved = removed.has(it.id);
              const upd = draft.find((d) => d.id === it.id);
              const qty = upd?.quantity ?? it.quantity;
              const price = upd?.unit_price ?? it.unit_price;
              const disc = upd?.discount_percent ?? it.discount_percent;
              const lineTotal = (
                qty * Number(price) * (100 - Number(disc)) / 100
              ).toFixed(2);

              return (
                <tr
                  key={it.id}
                  className={`border-t border-slate-100 ${isRemoved ? "opacity-40 line-through" : ""}`}
                >
                  <td className="px-4 py-2 font-mono text-xs">
                    {it.article || "—"}
                  </td>
                  <td className="px-4 py-2">{it.name}</td>
                  <td className="px-4 py-2 text-center">
                    {isEditable ? (
                      <input
                        type="number"
                        min={1}
                        max={10000}
                        value={qty}
                        disabled={isRemoved}
                        onChange={(e) =>
                          setDraft((arr) =>
                            arr.map((d) =>
                              d.id === it.id
                                ? {
                                    ...d,
                                    quantity: Math.max(1, Number(e.target.value) || 1),
                                  }
                                : d,
                            ),
                          )
                        }
                        className="input w-20 text-center"
                      />
                    ) : (
                      qty
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {isEditable ? (
                      <input
                        type="number"
                        min={0}
                        step="0.01"
                        value={price}
                        disabled={isRemoved}
                        onChange={(e) =>
                          setDraft((arr) =>
                            arr.map((d) =>
                              d.id === it.id
                                ? { ...d, unit_price: e.target.value }
                                : d,
                            ),
                          )
                        }
                        className="input w-28 text-right"
                      />
                    ) : (
                      `${price} ₽`
                    )}
                  </td>
                  <td className="px-4 py-2 text-center">
                    {isEditable ? (
                      <input
                        type="number"
                        min={0}
                        max={100}
                        step="0.01"
                        value={disc}
                        disabled={isRemoved}
                        onChange={(e) =>
                          setDraft((arr) =>
                            arr.map((d) =>
                              d.id === it.id
                                ? { ...d, discount_percent: e.target.value }
                                : d,
                            ),
                          )
                        }
                        className="input w-20 text-center"
                      />
                    ) : (
                      `${disc}%`
                    )}
                  </td>
                  <td className="px-4 py-2 text-right font-medium">
                    {lineTotal} ₽
                  </td>
                  {isEditable && (
                    <td className="px-4 py-2 text-right">
                      {isRemoved ? (
                        <button
                          onClick={() =>
                            setRemoved((s) => {
                              const ns = new Set(s);
                              ns.delete(it.id);
                              return ns;
                            })
                          }
                          className="text-slate-500 hover:underline text-xs"
                        >
                          вернуть
                        </button>
                      ) : (
                        <button
                          onClick={() =>
                            setRemoved((s) => new Set(s).add(it.id))
                          }
                          className="text-red-700 hover:underline text-xs"
                        >
                          ×
                        </button>
                      )}
                    </td>
                  )}
                </tr>
              );
            })}
            <tr className="border-t border-slate-200 bg-slate-50">
              <td
                colSpan={isEditable ? 5 : 5}
                className="px-4 py-2 text-right font-medium"
              >
                Итого
              </td>
              <td className="px-4 py-2 text-right font-semibold">
                {isEditable ? liveTotal : data.total_amount} ₽
              </td>
              {isEditable && <td></td>}
            </tr>
          </tbody>
        </table>
      </div>

      {isEditable && (
        <div className="card p-4 space-y-3">
          <div className="label">Добавить позицию в КП</div>
          <div className="flex gap-2">
            <input
              value={addSearch}
              onChange={(e) => setAddSearch(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") doAddSearch();
              }}
              placeholder="Поиск по артикулу или названию"
              className="input flex-1"
            />
            <button
              onClick={doAddSearch}
              disabled={addSearching}
              className="btn-secondary"
            >
              {addSearching ? "Поиск…" : "Найти"}
            </button>
          </div>
          {addResults.length > 0 && (
            <div className="border border-slate-200 rounded divide-y max-h-56 overflow-auto">
              {addResults.map((p) => (
                <div
                  key={p.id}
                  className="flex items-center justify-between px-3 py-2 text-sm"
                >
                  <div>
                    <div className="font-medium">{p.name}</div>
                    <div className="text-xs text-slate-500">
                      {p.article} · {p.price} ₽
                    </div>
                  </div>
                  <button
                    onClick={() => addPosition(p.id)}
                    disabled={busy}
                    className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-xs disabled:opacity-50"
                  >
                    + Добавить
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div className="card p-4">
          <div className="label">Условия оплаты</div>
          {isEditable ? (
            <textarea
              rows={3}
              value={paymentTerms}
              onChange={(e) => setPaymentTerms(e.target.value)}
              className="input"
              placeholder="Оплата по счёту в течение 5 рабочих дней"
            />
          ) : (
            <div className="text-sm text-slate-700 whitespace-pre-wrap">
              {data.payment_terms || (
                <span className="text-slate-400">не указаны</span>
              )}
            </div>
          )}
        </div>
        <div className="card p-4">
          <div className="label">Условия поставки</div>
          {isEditable ? (
            <textarea
              rows={3}
              value={deliveryTerms}
              onChange={(e) => setDeliveryTerms(e.target.value)}
              className="input"
              placeholder="Доставка курьером по Москве 1-2 рабочих дня"
            />
          ) : (
            <div className="text-sm text-slate-700 whitespace-pre-wrap">
              {data.delivery_terms || (
                <span className="text-slate-400">не указаны</span>
              )}
            </div>
          )}
        </div>
      </div>

      <div className="card p-4 flex flex-wrap gap-2">
        {isEditable && (
          <>
            <button
              disabled={busy}
              onClick={saveDraft}
              className="btn-secondary"
            >
              Сохранить черновик
            </button>
            <button
              disabled={busy}
              onClick={async () => {
                await saveDraft();
                await action(() => sendProposal(data.id));
              }}
              className="btn-primary"
            >
              Сохранить и отправить клиенту
            </button>
          </>
        )}

        {canAct && (
          <>
            <button
              disabled={busy}
              onClick={() => {
                if (confirm("Принять КП?")) action(() => acceptProposal(data.id));
              }}
              className="btn-primary"
            >
              Принять
            </button>
            <button
              disabled={busy}
              onClick={() => {
                const reason =
                  prompt("Причина отклонения (необязательно):", "") ?? "";
                if (confirm("Отклонить КП?"))
                  action(() => rejectProposal(data.id, reason || undefined));
              }}
              className="btn-danger"
            >
              Отклонить
            </button>
            <button
              disabled={busy}
              onClick={() => {
                if (confirm("Вернуть КП на пересчёт?"))
                  action(() => requestRevision(data.id));
              }}
              className="btn-secondary"
            >
              Запросить пересчёт
            </button>
          </>
        )}

        {!isEditable && !canAct && (
          <span className="text-sm text-slate-500 self-center">
            {data.status === "accepted"
              ? "КП принято клиентом — следующий шаг: создание заказа"
              : data.status === "rejected"
                ? "КП отклонено"
                : data.status === "sent"
                  ? "КП отправлено, ждём ответ клиента"
                  : null}
          </span>
        )}
      </div>
    </div>
  );
}

export function CreateProposalFromRequest({
  requestId,
  onCreated,
}: {
  requestId: string;
  onCreated: (cpId: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handle() {
    setBusy(true);
    setError(null);
    try {
      const cp = await createFromRequest(requestId);
      onCreated(cp.id);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <button onClick={handle} disabled={busy} className="btn-primary">
        {busy ? "Создаём…" : "Сформировать КП"}
      </button>
      {error && (
        <div className="text-xs text-red-700 mt-1">{error}</div>
      )}
    </>
  );
}
