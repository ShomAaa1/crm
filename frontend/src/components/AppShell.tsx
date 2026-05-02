import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

const ROLE_LABEL: Record<string, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
  client: "Клиент",
};

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  async function handleLogout() {
    await logout();
    navigate("/login", { replace: true });
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="text-lg font-semibold text-brand-700">
            АвтоДеталь <span className="text-slate-400 font-normal">CRM</span>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            {user?.role === "admin" && (
              <NavLink
                to="/admin/users"
                className={({ isActive }) =>
                  isActive
                    ? "text-brand-700 font-medium"
                    : "text-slate-600 hover:text-brand-700"
                }
              >
                Пользователи
              </NavLink>
            )}
          </nav>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <div className="text-right">
            <div className="font-medium">{user?.full_name}</div>
            <div className="text-slate-500 text-xs">
              {user?.role && ROLE_LABEL[user.role]}
            </div>
          </div>
          <button onClick={handleLogout} className="btn-secondary">
            Выйти
          </button>
        </div>
      </header>

      <main className="flex-1 p-6">
        <Outlet />
      </main>
    </div>
  );
}
