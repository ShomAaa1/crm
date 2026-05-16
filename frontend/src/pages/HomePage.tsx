import { Link } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

const ROLE_HINTS: Record<string, { title: string; body: string }> = {
  admin: {
    title: "Доступные разделы",
    body: "Управление пользователями и каталогом — см. ссылки в меню сверху.",
  },
  head: {
    title: "Доступные разделы",
    body: "Управление каталогом запчастей. Дашборд руководителя и контроль SLA — на следующих этапах.",
  },
  manager: {
    title: "Доступные разделы",
    body: "Управление каталогом запчастей. Заявки клиентов и формирование КП — на следующих этапах.",
  },
  client: {
    title: "Каталог запчастей",
    body: "Просмотр каталога, поиск по артикулу и фильтрация. Корзина, заявки и заказы — на следующих этапах.",
  },
};

export function HomePage() {
  const user = useAuthStore((s) => s.user);
  const hint = user ? ROLE_HINTS[user.role] : undefined;

  return (
    <div className="card p-6 max-w-2xl space-y-4">
      <div>
        <h2 className="text-xl font-semibold mb-1">
          Здравствуйте, {user?.full_name}!
        </h2>
        <p className="text-slate-600">Добро пожаловать в АвтоДеталь CRM.</p>
      </div>

      {hint && (
        <div className="rounded-md bg-slate-50 border border-slate-200 p-4">
          <div className="font-medium text-slate-800 mb-1">{hint.title}</div>
          <div className="text-sm text-slate-600">{hint.body}</div>
          <div className="mt-3 flex flex-wrap gap-3 text-sm">
            <Link to="/catalog" className="text-brand-700 hover:underline">
              → Каталог
            </Link>
            {(user?.role === "manager" ||
              user?.role === "head" ||
              user?.role === "admin") && (
              <>
                <Link to="/admin/parts" className="text-brand-700 hover:underline">
                  → Запчасти
                </Link>
                <Link to="/admin/categories" className="text-brand-700 hover:underline">
                  → Категории
                </Link>
              </>
            )}
            {user?.role === "admin" && (
              <Link to="/admin/users" className="text-brand-700 hover:underline">
                → Пользователи
              </Link>
            )}
          </div>
        </div>
      )}

      <div className="text-sm text-slate-500">
        <div>Email: {user?.email}</div>
        <div>Роль: {user?.role}</div>
      </div>
    </div>
  );
}
