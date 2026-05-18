import { FormEvent, useEffect, useState } from "react";
import { extractError } from "@/api/client";
import {
  blockUser,
  createUser,
  listUsers,
  unblockUser,
  type UserCreateInput,
} from "@/api/users";
import { PasswordInput } from "@/components/PasswordInput";
import type { User, UserRole } from "@/types";

const ROLE_LABEL: Record<UserRole, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
  client: "Клиент",
};

export function UsersPage() {
  const [items, setItems] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<UserRole | "">("");

  const [showCreate, setShowCreate] = useState(false);

  async function reload() {
    setLoading(true);
    setError(null);
    try {
      const page = await listUsers({
        search: search || undefined,
        role: roleFilter || undefined,
        limit: 50,
        offset: 0,
      });
      setItems(page.items);
      setTotal(page.total);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [roleFilter]);

  async function toggleBlock(u: User) {
    try {
      if (u.is_active) {
        await blockUser(u.id);
      } else {
        await unblockUser(u.id);
      }
      await reload();
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">Пользователи</h2>
        <button onClick={() => setShowCreate(true)} className="btn-primary">
          + Создать
        </button>
      </div>

      <div className="card p-4 flex gap-3 items-end">
        <div className="flex-1">
          <label className="label">Поиск (email или ФИО)</label>
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && reload()}
            className="input"
            placeholder="например, manager"
          />
        </div>
        <div className="w-56">
          <label className="label">Роль</label>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value as UserRole | "")}
            className="input"
          >
            <option value="">Все</option>
            <option value="admin">Администраторы</option>
            <option value="head">Руководители</option>
            <option value="manager">Менеджеры</option>
            <option value="client">Клиенты</option>
          </select>
        </div>
        <button onClick={reload} className="btn-secondary">
          Применить
        </button>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      <div className="card overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 text-slate-600">
            <tr>
              <th className="text-left px-4 py-2">Email</th>
              <th className="text-left px-4 py-2">ФИО</th>
              <th className="text-left px-4 py-2">Роль</th>
              <th className="text-left px-4 py-2">Телефон</th>
              <th className="text-left px-4 py-2">Статус</th>
              <th className="text-right px-4 py-2">Действия</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  Загрузка…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-slate-500">
                  Ничего не найдено
                </td>
              </tr>
            )}
            {!loading &&
              items.map((u) => (
                <tr key={u.id} className="border-t border-slate-100">
                  <td className="px-4 py-2">{u.email}</td>
                  <td className="px-4 py-2">{u.full_name}</td>
                  <td className="px-4 py-2">{ROLE_LABEL[u.role]}</td>
                  <td className="px-4 py-2 text-slate-500">{u.phone || "—"}</td>
                  <td className="px-4 py-2">
                    {u.is_active ? (
                      <span className="text-green-700 bg-green-100 px-2 py-0.5 rounded text-xs">
                        активен
                      </span>
                    ) : (
                      <span className="text-red-700 bg-red-100 px-2 py-0.5 rounded text-xs">
                        заблокирован
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-2 text-right">
                    <button
                      onClick={() => toggleBlock(u)}
                      className={u.is_active ? "btn-danger" : "btn-secondary"}
                    >
                      {u.is_active ? "Заблокировать" : "Разблокировать"}
                    </button>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>
      </div>

      <div className="text-xs text-slate-500">Всего: {total}</div>

      {showCreate && (
        <CreateUserDialog
          onClose={() => setShowCreate(false)}
          onCreated={async () => {
            setShowCreate(false);
            await reload();
          }}
        />
      )}
    </div>
  );
}

function CreateUserDialog({
  onClose,
  onCreated,
}: {
  onClose: () => void;
  onCreated: () => void | Promise<void>;
}) {
  const [form, setForm] = useState<UserCreateInput>({
    email: "",
    password: "",
    role: "manager",
    full_name: "",
    phone: "",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await createUser({
        ...form,
        phone: form.phone || null,
      });
      await onCreated();
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-10">
      <div className="card w-full max-w-md p-6">
        <h3 className="text-lg font-semibold mb-4">Новый пользователь</h3>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              required
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="label">ФИО</label>
            <input
              required
              value={form.full_name}
              onChange={(e) => setForm({ ...form, full_name: e.target.value })}
              className="input"
            />
          </div>
          <div>
            <label className="label">Роль</label>
            <select
              value={form.role}
              onChange={(e) =>
                setForm({ ...form, role: e.target.value as UserRole })
              }
              className="input"
            >
              <option value="manager">Менеджер</option>
              <option value="head">Руководитель</option>
              <option value="client">Клиент</option>
              <option value="admin">Администратор</option>
            </select>
          </div>
          <div>
            <label className="label">Пароль</label>
            <PasswordInput
              required
              minLength={8}
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="input"
            />
            <p className="text-xs text-slate-500 mt-1">
              Минимум 8 символов, должна быть буква и цифра
            </p>
          </div>
          <div>
            <label className="label">Телефон</label>
            <input
              value={form.phone || ""}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="input"
              placeholder="+7 (495) 000-00-00"
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
              {loading ? "Создаём…" : "Создать"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
