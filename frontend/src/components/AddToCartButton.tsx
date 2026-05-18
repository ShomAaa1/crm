import { useState } from "react";
import { Link } from "react-router-dom";
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
  const currentInCart = useCartStore(
    (s) => s.summary?.items.find((i) => i.part_id === partId)?.quantity ?? 0,
  );

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

  const inCart = currentInCart > 0;

  if (compact) {
    return (
      <button
        disabled={adding || okFlash || !inStock}
        onClick={onAdd}
        className="btn-primary text-sm"
        title={inStock ? "Добавить в корзину" : "Нет в наличии"}
      >
        {okFlash
          ? "✓"
          : inCart
            ? `В корзине: ${currentInCart} +`
            : "+ В корзину"}
      </button>
    );
  }

  return (
    <div className="space-y-2">
      {inCart && (
        <div className="flex items-center gap-2 text-sm text-green-800 bg-green-50 border border-green-200 rounded px-3 py-2">
          <span>
            Уже в корзине: <span className="font-medium">{currentInCart}</span> шт
          </span>
          <Link to="/cart" className="ml-auto text-brand-700 hover:underline">
            Перейти в корзину →
          </Link>
        </div>
      )}

      <div className="flex items-center gap-2">
        <label className="text-sm text-slate-600">
          {inCart ? "Добавить ещё:" : "Количество:"}
        </label>
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
          {adding
            ? "Добавляем…"
            : okFlash
              ? "✓ Добавлено"
              : inCart
                ? "Добавить ещё"
                : "В корзину"}
        </button>
      </div>
      {!inStock && (
        <div className="text-xs text-amber-700">Нет в наличии</div>
      )}
      {error && <div className="text-xs text-red-700">{error}</div>}
    </div>
  );
}
