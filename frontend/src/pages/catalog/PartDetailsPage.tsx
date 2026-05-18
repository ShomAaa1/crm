import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { extractError } from "@/api/client";
import { getPart } from "@/api/catalog";
import { AddToCartButton } from "@/components/AddToCartButton";
import type { Part } from "@/types";

export function PartDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const [part, setPart] = useState<Part | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    setError(null);
    getPart(id)
      .then(setPart)
      .catch((e) => setError(extractError(e)))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <div className="text-slate-500">Загрузка…</div>;
  if (error)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
        {error}
      </div>
    );
  if (!part) return null;

  const price = Number(part.price).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const inStock = part.stock_quantity > 0;

  return (
    <div className="space-y-4 max-w-3xl">
      <Link to="/catalog" className="text-sm text-brand-700 hover:underline">
        ← К каталогу
      </Link>

      <div className="card p-6">
        <div className="text-xs text-slate-500 mb-1">{part.article}</div>
        <h1 className="text-2xl font-semibold mb-2">{part.name}</h1>
        {part.manufacturer && (
          <div className="text-slate-600 mb-4">Производитель: {part.manufacturer}</div>
        )}

        <div className="flex items-center gap-4 mb-4">
          <div className="text-3xl font-bold text-brand-700">
            {price} ₽
            <span className="text-base text-slate-500 font-normal"> / {part.unit}</span>
          </div>
          {inStock ? (
            <span className="text-sm text-green-700 bg-green-100 px-3 py-1 rounded">
              в наличии: {part.stock_quantity} {part.unit}
            </span>
          ) : (
            <span className="text-sm text-red-700 bg-red-100 px-3 py-1 rounded">
              нет в наличии
            </span>
          )}
        </div>

        <div className="mt-4 pt-4 border-t border-slate-200">
          <AddToCartButton partId={part.id} inStock={inStock} />
        </div>

        {part.description && (
          <div className="mt-4 pt-4 border-t border-slate-200">
            <div className="text-sm font-medium text-slate-700 mb-1">Описание</div>
            <div className="text-sm text-slate-700 whitespace-pre-line">
              {part.description}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
