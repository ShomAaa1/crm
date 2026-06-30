import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { extractError } from "@/api/client";
import { listClients, type ClientListItem } from "@/api/clients";
import { listParts } from "@/api/catalog";
import { createRequestForClient } from "@/api/requests";
import { createFromRequest } from "@/api/proposals";
import type { Part } from "@/types";

interface Line {
  part: Part;
  quantity: number;
}

export function CreateRequestForClientPage() {
  const navigate = useNavigate();

  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [clientId, setClientId] = useState("");
  const [comment, setComment] = useState("");

  const [search, setSearch] = useState("");
  const [results, setResults] = useState<Part[]>([]);
  const [searching, setSearching] = useState(false);

  const [lines, setLines] = useState<Line[]>([]);

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listClients()
      .then(setClients)
      .catch((e) => setError(extractError(e)));
  }, []);

  async function doSearch() {
    setSearching(true);
    setError(null);
    try {
      const page = await listParts({
        search: search.trim() || undefined,
        is_active: true,
        limit: 20,
      });
      setResults(page.items);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setSearching(false);
    }
  }

  function addPart(part: Part) {
    setLines((prev) => {
      const existing = prev.find((l) => l.part.id === part.id);
      if (existing) {
        return prev.map((l) =>
          l.part.id === part.id ? { ...l, quantity: l.quantity + 1 } : l,
        );
      }
      return [...prev, { part, quantity: 1 }];
    });
  }

  function setQty(partId: string, qty: number) {
    setLines((prev) =>
      prev.map((l) =>
        l.part.id === partId ? { ...l, quantity: Math.max(1, qty || 1) } : l,
      ),
    );
  }

  function removeLine(partId: string) {
    setLines((prev) => prev.filter((l) => l.part.id !== partId));
  }

  const total = lines.reduce(
    (sum, l) => sum + Number(l.part.price) * l.quantity,
    0,
  );

  async function submit() {
    if (!clientId) {
      setError("Выберите клиента");
      return;
    }
    if (lines.length === 0) {
      setError("Добавьте хотя бы одну позицию");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const request = await createRequestForClient({
        client_id: clientId,
        items: lines.map((l) => ({ part_id: l.part.id, quantity: l.quantity })),
        comment: comment.trim() || null,
      });
      // Сразу ведём менеджера к формированию КП по созданной заявке.
      try {
        const cp = await createFromRequest(request.id);
        navigate(`/proposals/${cp.id}`);
      } catch {
        navigate(`/requests/${request.id}`);
      }
    } catch (e) {
      setError(extractError(e));
      setSubmitting(false);
    }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">Оформить заявку для клиента</h2>
      <p className="text-sm text-slate-500">
        Заявка оформляется менеджером от имени клиента. После создания
        откроется формирование коммерческого предложения.
      </p>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="card p-4 space-y-3">
        <div>
          <label className="label">Клиент</label>
          <select
            value={clientId}
            onChange={(e) => setClientId(e.target.value)}
            className="input"
          >
            <option value="">— выберите клиента —</option>
            {clients.map((c) => (
              <option key={c.id} value={c.id}>
                {c.company_name} (ИНН {c.inn})
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Комментарий (необязательно)</label>
          <textarea
            value={comment}
            onChange={(e) => setComment(e.target.value)}
            className="input"
            rows={2}
          />
        </div>
      </div>

      <div className="card p-4 space-y-3">
        <label className="label">Добавить позиции из каталога</label>
        <div className="flex gap-2">
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") doSearch();
            }}
            placeholder="Поиск по артикулу или названию"
            className="input flex-1"
          />
          <button
            onClick={doSearch}
            disabled={searching}
            className="px-3 py-1.5 rounded bg-brand-600 text-white text-sm disabled:opacity-50"
          >
            {searching ? "Поиск…" : "Найти"}
          </button>
        </div>
        {results.length > 0 && (
          <div className="border border-slate-200 rounded divide-y max-h-64 overflow-auto">
            {results.map((p) => (
              <div
                key={p.id}
                className="flex items-center justify-between px-3 py-2 text-sm"
              >
                <div>
                  <div className="font-medium">{p.name}</div>
                  <div className="text-xs text-slate-500">
                    {p.article} · {p.price} ₽ · остаток {p.stock_quantity}
                  </div>
                </div>
                <button
                  onClick={() => addPart(p)}
                  className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-xs"
                >
                  + Добавить
                </button>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">Позиция</th>
              <th className="text-left px-4 py-2">Артикул</th>
              <th className="text-right px-4 py-2">Цена</th>
              <th className="text-center px-4 py-2">Кол-во</th>
              <th className="text-right px-4 py-2">Сумма</th>
              <th className="px-4 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {lines.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  Позиции не добавлены
                </td>
              </tr>
            )}
            {lines.map((l) => (
              <tr key={l.part.id} className="border-t border-slate-100">
                <td className="px-4 py-2">{l.part.name}</td>
                <td className="px-4 py-2 font-mono text-xs">{l.part.article}</td>
                <td className="px-4 py-2 text-right">{l.part.price} ₽</td>
                <td className="px-4 py-2 text-center">
                  <input
                    type="number"
                    min={1}
                    value={l.quantity}
                    onChange={(e) => setQty(l.part.id, Number(e.target.value))}
                    className="input w-20 text-center"
                  />
                </td>
                <td className="px-4 py-2 text-right font-medium">
                  {(Number(l.part.price) * l.quantity).toFixed(2)} ₽
                </td>
                <td className="px-4 py-2 text-right">
                  <button
                    onClick={() => removeLine(l.part.id)}
                    className="text-red-600 hover:underline text-xs"
                  >
                    удалить
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between">
        <div className="text-sm text-slate-600">
          Итого: <span className="font-semibold">{total.toFixed(2)} ₽</span>
        </div>
        <button
          onClick={submit}
          disabled={submitting}
          className="px-4 py-2 rounded bg-brand-600 text-white text-sm disabled:opacity-50"
        >
          {submitting ? "Создание…" : "Создать заявку и перейти к КП"}
        </button>
      </div>
    </div>
  );
}
