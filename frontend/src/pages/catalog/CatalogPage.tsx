import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { extractError } from "@/api/client";
import { getCategoryTree, listParts } from "@/api/catalog";
import { CategoryTree } from "@/components/CategoryTree";
import type { CategoryTreeNode, Part } from "@/types";

export function CatalogPage() {
  const [tree, setTree] = useState<CategoryTreeNode[]>([]);
  const [parts, setParts] = useState<Part[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [inStockOnly, setInStockOnly] = useState(false);

  useEffect(() => {
    getCategoryTree()
      .then(setTree)
      .catch((e) => setError(extractError(e)));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    listParts({
      category_id: categoryId ?? undefined,
      search: search || undefined,
      in_stock: inStockOnly || undefined,
      limit: 100,
      offset: 0,
    })
      .then((page) => {
        setParts(page.items);
        setTotal(page.total);
      })
      .catch((e) => setError(extractError(e)))
      .finally(() => setLoading(false));
  }, [categoryId, search, inStockOnly]);

  function applySearch(e: React.FormEvent) {
    e.preventDefault();
    setSearch(searchInput.trim());
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[260px_1fr] gap-4">
      <div>
        <CategoryTree nodes={tree} selectedId={categoryId} onSelect={setCategoryId} />
      </div>

      <div className="space-y-4">
        <form onSubmit={applySearch} className="card p-3 flex gap-2 items-center">
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Артикул, название или производитель"
            className="input"
          />
          <label className="flex items-center gap-2 text-sm text-slate-700 whitespace-nowrap">
            <input
              type="checkbox"
              checked={inStockOnly}
              onChange={(e) => setInStockOnly(e.target.checked)}
            />
            Только в наличии
          </label>
          <button type="submit" className="btn-primary">
            Найти
          </button>
          {search && (
            <button
              type="button"
              onClick={() => {
                setSearch("");
                setSearchInput("");
              }}
              className="btn-secondary"
            >
              Сбросить
            </button>
          )}
        </form>

        {error && (
          <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
            {error}
          </div>
        )}

        <div className="text-sm text-slate-500">
          {loading ? "Загрузка…" : `Найдено: ${total}`}
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
          {parts.map((p) => (
            <PartCard key={p.id} part={p} />
          ))}
          {!loading && parts.length === 0 && (
            <div className="card p-6 text-center text-slate-500 col-span-full">
              Ничего не найдено
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function PartCard({ part }: { part: Part }) {
  const price = Number(part.price).toLocaleString("ru-RU", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const inStock = part.stock_quantity > 0;

  return (
    <Link
      to={`/catalog/${part.id}`}
      className="card p-4 hover:border-brand-500 transition-colors flex flex-col"
    >
      <div className="text-xs text-slate-500 mb-1">{part.article}</div>
      <div className="font-medium text-slate-900 mb-1 line-clamp-2">{part.name}</div>
      {part.manufacturer && (
        <div className="text-xs text-slate-500 mb-2">{part.manufacturer}</div>
      )}
      <div className="mt-auto flex items-end justify-between pt-2">
        <div className="text-lg font-semibold text-brand-700">
          {price} ₽<span className="text-xs text-slate-500 font-normal"> / {part.unit}</span>
        </div>
        {inStock ? (
          <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded">
            в наличии: {part.stock_quantity}
          </span>
        ) : (
          <span className="text-xs text-red-700 bg-red-100 px-2 py-0.5 rounded">
            нет в наличии
          </span>
        )}
      </div>
    </Link>
  );
}
