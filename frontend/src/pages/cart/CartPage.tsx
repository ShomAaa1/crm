import { FormEvent, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useCartStore } from "@/store/cart";
import { extractError } from "@/api/client";
import { createRequest } from "@/api/requests";

export function CartPage() {
  const summary = useCartStore((s) => s.summary);
  const refresh = useCartStore((s) => s.refresh);
  const setQty = useCartStore((s) => s.setQty);
  const remove = useCartStore((s) => s.remove);
  const clear = useCartStore((s) => s.clear);

  const navigate = useNavigate();
  const [showModal, setShowModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    refresh();
  }, [refresh]);

  if (!summary) {
    return <div className="text-slate-500">Загрузка…</div>;
  }

  if (summary.items.length === 0) {
    return (
      <div className="card p-6 max-w-xl">
        <h2 className="text-xl font-semibold mb-2">Корзина пуста</h2>
        <p className="text-slate-600 mb-4">
          Добавьте запчасти из каталога, чтобы оформить заявку.
        </p>
        <Link to="/catalog" className="btn-primary">
          Перейти в каталог
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Корзина</h2>
        <button
          onClick={async () => {
            if (confirm("Очистить корзину полностью?")) {
              await clear();
            }
          }}
          className="btn-secondary text-sm"
        >
          Очистить
        </button>
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
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {summary.items.map((it) => (
              <tr key={it.id} className="border-t border-slate-100">
                <td className="px-4 py-2 font-mono text-xs">{it.article}</td>
                <td className="px-4 py-2">
                  <div>{it.name}</div>
                  {it.manufacturer && (
                    <div className="text-xs text-slate-500">{it.manufacturer}</div>
                  )}
                  {!it.in_stock && (
                    <div className="text-xs text-amber-700">⚠ Нет в наличии</div>
                  )}
                </td>
                <td className="px-4 py-2 text-right">{it.price} ₽</td>
                <td className="px-4 py-2 text-center">
                  <input
                    type="number"
                    min={1}
                    max={10000}
                    value={it.quantity}
                    onChange={(e) =>
                      setQty(
                        it.part_id,
                        Math.max(1, Number(e.target.value) || 1),
                      )
                    }
                    className="input w-20 text-center"
                  />
                </td>
                <td className="px-4 py-2 text-right font-medium">
                  {it.line_total} ₽
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => remove(it.part_id)}
                    className="text-red-700 hover:underline text-sm"
                  >
                    Удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card p-4 flex items-center justify-between">
        <div className="text-sm text-slate-600">
          Позиций: <span className="font-medium">{summary.items_count}</span>
        </div>
        <div className="text-lg">
          Итого: <span className="font-semibold">{summary.total} ₽</span>
        </div>
        <button onClick={() => setShowModal(true)} className="btn-primary">
          Оформить заявку
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {showModal && (
        <SubmitModal
          onCancel={() => setShowModal(false)}
          onSubmit={async (comment) => {
            setError(null);
            try {
              const r = await createRequest(comment || null);
              await clear();
              navigate(`/requests/${r.id}`);
            } catch (err) {
              setError(extractError(err));
              setShowModal(false);
            }
          }}
        />
      )}
    </div>
  );
}

function SubmitModal({
  onCancel,
  onSubmit,
}: {
  onCancel: () => void;
  onSubmit: (comment: string) => void | Promise<void>;
}) {
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  async function handle(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    await onSubmit(comment.trim());
    setBusy(false);
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-10">
      <div className="card w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-3">Оформление заявки</h3>
        <p className="text-sm text-slate-600 mb-3">
          После отправки заявка попадёт менеджеру. Корзина будет очищена.
        </p>
        <form onSubmit={handle} className="space-y-3">
          <div>
            <label className="label">Комментарий (необязательно)</label>
            <textarea
              rows={4}
              value={comment}
              onChange={(e) => setComment(e.target.value)}
              className="input"
              placeholder="Например: срочно, нужно к пятнице"
            />
          </div>
          <div className="flex justify-end gap-2">
            <button type="button" onClick={onCancel} className="btn-secondary">
              Отмена
            </button>
            <button type="submit" disabled={busy} className="btn-primary">
              {busy ? "Отправляем…" : "Отправить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
