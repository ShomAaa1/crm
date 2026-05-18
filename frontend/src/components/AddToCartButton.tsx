import { useState } from "react";
import { useCartStore } from "@/store/cart";
import { useAuthStore } from "@/store/auth";
import { extractError } from "@/api/client";

interface Props {
  partId: string;
  inStock: boolean;
  compact?: boolean;
}

export function AddToCartButton({ partId, inStock, compact = false }: Props) {
  const user = useAuthStore((s) => s.user);
  const add = useCartStore((s) => s.add);

  const [qty, setQty] = useState(1);
  const [adding, setAdding] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okFlash, setOkFlash] = useState(false);

  if (user?.role !== "client") return null;

  async function onAdd() {
    setAdding(true);
    setError(null);
    try {
      await add(partId, qty);
      setOkFlash(true);
      setTimeout(() => setOkFlash(false), 1200);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setAdding(false);
    }
  }

  if (compact) {
    return (
      <button
        disabled={adding || okFlash || !inStock}
        onClick={onAdd}
        className="btn-primary text-sm"
        title={inStock ? "Добавить в корзину" : "Нет в наличии"}
      >
        {okFlash ? "✓" : "+ В корзину"}
      </button>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-600">Количество:</label>
        <input
          type="number"
          min={1}
          max={10000}
          value={qty}
          onChange={(e) => setQty(Math.max(1, Number(e.target.value) || 1))}
          className="input w-24"
        />
        <button
          disabled={adding || okFlash || !inStock}
          onClick={onAdd}
          className="btn-primary"
        >
          {adding ? "Добавляем…" : okFlash ? "✓ Добавлено" : "В корзину"}
        </button>
      </div>
      {!inStock && (
        <div className="text-xs text-amber-700">Нет в наличии</div>
      )}
      {error && <div className="text-xs text-red-700">{error}</div>}
    </div>
  );
}
