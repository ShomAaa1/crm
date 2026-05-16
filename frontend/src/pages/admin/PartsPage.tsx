import { FormEvent, useEffect, useRef, useState } from "react";
import { extractError } from "@/api/client";
import {
  activatePart,
  createPart,
  deactivatePart,
  importCsv,
  listCategories,
  listParts,
  updatePart,
  type PartInput,
} from "@/api/catalog";
import type { Category, CsvImportResult, Part } from "@/types";

export function PartsPage() {
  const [items, setItems] = useState<Part[]>([]);
  const [total, setTotal] = useState(0);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [categoryFilter, setCategoryFilter] = useState<string>("");
  const [activeFilter, setActiveFilter] = useState<"all" | "active" | "inactive">("active");

  const [editing, setEditing] = useState<Part | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  const [importResult, setImportResult] = useState<CsvImportResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const page = await listParts({
        search: search || undefined,
        category_id: categoryFilter || undefined,
        is_active:
          activeFilter === "all" ? undefined : activeFilter === "active",
        limit: 100,
      });
      setItems(page.items);
      setTotal(page.total);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    listCategories().then(setCategories).catch((e) => setError(extractError(e)));
  }, []);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, categoryFilter, activeFilter]);

  async function toggleActive(p: Part) {
    try {
      if (p.is_active) {
        await deactivatePart(p.id);
      } else {
        await activatePart(p.id);
      }
      await reload();
    } catch (e) {
      setError(extractError(e));
    }
  }

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setError(null);
    setImportResult(null);
    try {
      const result = await importCsv(file);
      setImportResult(result);
      await reload();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  const categoryName = (id: string | null) =>
    categories.find((c) => c.id === id)?.name ?? "—";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h2 className="text-xl font-semibold">Запчасти</h2>
        <div className="flex gap-2">
          <button
            onClick={() => fileInputRef.current?.click()}
            className="btn-secondary"
          >
            Импорт CSV
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,text/csv"
            onChange={handleFile}
            className="hidden"
          />
          <button onClick={() => setShowCreate(true)} className="btn-primary">
            + Создать
          </button>
        </div>
      </div>

      <div className="card p-4 grid grid-cols-1 md:grid-cols-[1fr_240px_200px_auto] gap-3 items-end">
        <div>
          <label className="label">Поиск</label>
          <input
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && setSearch(searchInput.trim())}
            className="input"
            placeholder="артикул или название"
          />
        </div>
        <div>
          <label className="label">Категория</label>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="input"
          >
            <option value="">Все</option>
            {categories.map((c) => (
              <option key={c.id} value={c.id}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="label">Статус</label>
          <select
            value={activeFilter}
            onChange={(e) => setActiveFilter(e.target.value as typeof activeFilter)}
            className="input"
          >
            <option value="active">Активные</option>
            <option value="inactive">Деактивированные</option>
            <option value="all">Все</option>
          </select>
        </div>
        <button onClick={() => setSearch(searchInput.trim())} className="btn-secondary">
          Применить
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {importResult && (
        <div className="card p-4 bg-blue-50 border-blue-200">
          <div className="font-medium mb-2">Результат импорта CSV</div>
          <div className="text-sm">
            Создано: <b>{importResult.created}</b>, обновлено:{" "}
            <b>{importResult.updated}</b>, цен изменено:{" "}
            <b>{importResult.price_changes}</b>, ошибок:{" "}
            <b>{importResult.errors.length}</b>
          </div>
          {importResult.errors.length > 0 && (
            <ul className="mt-2 text-xs text-red-700 space-y-0.5 max-h-32 overflow-y-auto">
              {importResult.errors.map((e, i) => (
                <li key={i}>
                  Строка {e.line}: {e.reason}
                </li>
              ))}
            </ul>
          )}
          <button
            onClick={() => setImportResult(null)}
            className="mt-2 text-xs text-blue-700 hover:underline"
          >
            Скрыть
          </button>
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-3 py-2">Артикул</th>
              <th className="text-left px-3 py-2">Название</th>
              <th className="text-left px-3 py-2">Категория</th>
              <th className="text-right px-3 py-2">Цена</th>
              <th className="text-right px-3 py-2">Остаток</th>
              <th className="text-left px-3 py-2">Статус</th>
              <th className="text-right px-3 py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading &&
              items.map((p) => (
                <tr key={p.id} className="border-t border-slate-100">
                  <td className="px-3 py-2 font-mono text-xs">{p.article}</td>
                  <td className="px-3 py-2">{p.name}</td>
                  <td className="px-3 py-2 text-slate-600">
                    {categoryName(p.category_id)}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {Number(p.price).toLocaleString("ru-RU", {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}
                  </td>
                  <td className="px-3 py-2 text-right">
                    {p.stock_quantity} {p.unit}
                  </td>
                  <td className="px-3 py-2">
                    {p.is_active ? (
                      <span className="text-xs text-green-700 bg-green-100 px-2 py-0.5 rounded">
                        активна
                      </span>
                    ) : (
                      <span className="text-xs text-slate-700 bg-slate-200 px-2 py-0.5 rounded">
                        скрыта
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-right whitespace-nowrap">
                    <button
                      onClick={() => setEditing(p)}
                      className="btn-secondary text-xs mr-1"
                    >
                      Изменить
                    </button>
                    <button
                      onClick={() => toggleActive(p)}
                      className={p.is_active ? "btn-danger text-xs" : "btn-secondary text-xs"}
                    >
                      {p.is_active ? "Скрыть" : "Вернуть"}
                    </button>
                  </td>
                </tr>
              ))}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                  Ничего не найдено
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-500">Всего: {total}</div>

      {(showCreate || editing) && (
        <PartDialog
          editing={editing}
          categories={categories}
          onClose={() => {
            setShowCreate(false);
            setEditing(null);
          }}
          onSaved={async () => {
            setShowCreate(false);
            setEditing(null);
            await reload();
          }}
        />
      )}
    </div>
  );
}

function PartDialog({
  editing,
  categories,
  onClose,
  onSaved,
}: {
  editing: Part | null;
  categories: Category[];
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const [form, setForm] = useState<PartInput>({
    article: editing?.article ?? "",
    name: editing?.name ?? "",
    description: editing?.description ?? "",
    manufacturer: editing?.manufacturer ?? "",
    category_id: editing?.category_id ?? null,
    price: editing?.price ?? "0",
    stock_quantity: editing?.stock_quantity ?? 0,
    unit: editing?.unit ?? "шт",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const payload = {
        ...form,
        description: form.description || null,
        manufacturer: form.manufacturer || null,
        category_id: form.category_id || null,
      };
      if (editing) {
        await updatePart(editing.id, payload);
      } else {
        await createPart(payload);
      }
      await onSaved();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-10 overflow-y-auto">
      <div className="card w-full max-w-lg p-6 my-8">
        <h3 className="text-lg font-semibold mb-4">
          {editing ? `Изменить ${editing.article}` : "Новая запчасть"}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">Артикул *</label>
              <input
                required
                value={form.article}
                onChange={(e) => setForm({ ...form, article: e.target.value })}
                className="input font-mono"
              />
            </div>
            <div>
              <label className="label">Производитель</label>
              <input
                value={form.manufacturer ?? ""}
                onChange={(e) => setForm({ ...form, manufacturer: e.target.value })}
                className="input"
              />
            </div>
          </div>
          <div>
            <label className="label">Название *</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="label">Категория</label>
            <select
              value={form.category_id ?? ""}
              onChange={(e) =>
                setForm({ ...form, category_id: e.target.value || null })
              }
              className="input"
            >
              <option value="">— без категории —</option>
              {categories.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="label">Цена *</label>
              <input
                required
                type="number"
                step="0.01"
                min="0"
                value={form.price as string}
                onChange={(e) => setForm({ ...form, price: e.target.value })}
                className="input"
              />
            </div>
            <div>
              <label className="label">Остаток</label>
              <input
                type="number"
                min="0"
                value={form.stock_quantity ?? 0}
                onChange={(e) =>
                  setForm({ ...form, stock_quantity: Number(e.target.value) })
                }
                className="input"
              />
            </div>
            <div>
              <label className="label">Единица</label>
              <input
                value={form.unit ?? "шт"}
                onChange={(e) => setForm({ ...form, unit: e.target.value })}
                className="input"
              />
            </div>
          </div>
          <div>
            <label className="label">Описание</label>
            <textarea
              value={form.description ?? ""}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              rows={3}
              className="input"
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">
              Отмена
            </button>
            <button type="submit" disabled={loading} className="btn-primary">
              {loading ? "Сохраняем…" : editing ? "Сохранить" : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
