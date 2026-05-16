import { FormEvent, useEffect, useState } from "react";
import { extractError } from "@/api/client";
import {
  createCategory,
  deleteCategory,
  getCategoryTree,
  updateCategory,
  listCategories,
  type CategoryInput,
} from "@/api/catalog";
import type { Category, CategoryTreeNode } from "@/types";

export function CategoriesPage() {
  const [flat, setFlat] = useState<Category[]>([]);
  const [tree, setTree] = useState<CategoryTreeNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [editing, setEditing] = useState<Category | null>(null);
  const [showCreate, setShowCreate] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const [t, f] = await Promise.all([getCategoryTree(), listCategories()]);
      setTree(t);
      setFlat(f);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
  }, []);

  async function handleDelete(c: Category) {
    if (!confirm(`Удалить категорию «${c.name}»?`)) return;
    try {
      await deleteCategory(c.id);
      await reload();
    } catch (e) {
      setError(extractError(e));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Категории каталога</h2>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          + Создать
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {loading && <div className="text-slate-500">Загрузка…</div>}

      <div className="card p-4">
        <CategoryNodes
          nodes={tree}
          onEdit={setEditing}
          onDelete={handleDelete}
        />
        {!loading && tree.length === 0 && (
          <div className="text-slate-500 text-center py-4">
            Пока нет ни одной категории
          </div>
        )}
      </div>

      {(showCreate || editing) && (
        <CategoryDialog
          flat={flat}
          editing={editing}
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

function CategoryNodes({
  nodes,
  onEdit,
  onDelete,
  depth = 0,
}: {
  nodes: CategoryTreeNode[];
  onEdit: (c: Category) => void;
  onDelete: (c: Category) => void;
  depth?: number;
}) {
  return (
    <div className="space-y-1">
      {nodes.map((n) => (
        <div key={n.id}>
          <div
            className="flex items-center justify-between py-1 rounded hover:bg-slate-50 px-2"
            style={{ paddingLeft: 8 + depth * 16 }}
          >
            <div>
              <span className="font-medium">{n.name}</span>{" "}
              <span className="text-xs text-slate-500">/ {n.slug}</span>
            </div>
            <div className="flex gap-2">
              <button onClick={() => onEdit(n)} className="btn-secondary text-xs">
                Изменить
              </button>
              <button onClick={() => onDelete(n)} className="btn-danger text-xs">
                Удалить
              </button>
            </div>
          </div>
          {n.children.length > 0 && (
            <CategoryNodes
              nodes={n.children}
              onEdit={onEdit}
              onDelete={onDelete}
              depth={depth + 1}
            />
          )}
        </div>
      ))}
    </div>
  );
}

function CategoryDialog({
  flat,
  editing,
  onClose,
  onSaved,
}: {
  flat: Category[];
  editing: Category | null;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const [form, setForm] = useState<CategoryInput>({
    name: editing?.name ?? "",
    slug: editing?.slug ?? "",
    parent_id: editing?.parent_id ?? null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      if (editing) {
        await updateCategory(editing.id, form);
      } else {
        await createCategory(form);
      }
      await onSaved();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  const parentOptions = flat.filter((c) => c.id !== editing?.id);

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-10">
      <div className="card w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">
          {editing ? "Изменить категорию" : "Новая категория"}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="label">Название</label>
            <input
              required
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="label">Slug (латиница, lower-case-with-dashes)</label>
            <input
              required
              value={form.slug}
              onChange={(e) => setForm({ ...form, slug: e.target.value })}
              className="input font-mono"
              pattern="^[a-z0-9]+(?:-[a-z0-9]+)*$"
            />
          </div>
          <div>
            <label className="label">Родительская категория</label>
            <select
              value={form.parent_id ?? ""}
              onChange={(e) =>
                setForm({ ...form, parent_id: e.target.value || null })
              }
              className="input"
            >
              <option value="">— верхний уровень —</option>
              {parentOptions.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.slug})
                </option>
              ))}
            </select>
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
