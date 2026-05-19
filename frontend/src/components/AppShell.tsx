import { useEffect } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { useCartStore } from "@/store/cart";

const ROLE_LABEL: Record<string, string> = {
  admin: "Администратор",
  head: "Руководитель",
  manager: "Менеджер",
  client: "Клиент",
};

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  isActive
    ? "text-brand-700 font-medium"
    : "text-slate-600 hover:text-brand-700";

export function AppShell() {
  const user = useAuthStore((s) => s.user);
  const logout = useAuthStore((s) => s.logout);
  const cartSummary = useCartStore((s) => s.summary);
  const refreshCart = useCartStore((s) => s.refresh);
  const resetCart = useCartStore((s) => s.reset);

  const navigate = useNavigate();

  const isClient = user?.role === "client";
  const isManagerSide =
    user?.role === "manager" || user?.role === "head" || user?.role === "admin";

  useEffect(() => {
    if (isClient) {
      refreshCart();
    } else {
      resetCart();
    }
  }, [isClient, refreshCart, resetCart]);

  async function handleLogout() {
    await logout();
    resetCart();
    navigate("/login", { replace: true });
  }

  const cartCount = cartSummary?.items_count ?? 0;

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-8">
          <div className="text-lg font-semibold text-brand-700">
            АвтоДеталь <span className="text-slate-400 font-normal">CRM</span>
          </div>
          <nav className="flex items-center gap-4 text-sm">
            <NavLink to="/catalog" className={navLinkClass}>
              Каталог
            </NavLink>

            {isClient && (
              <>
                <NavLink to="/cart" className={navLinkClass}>
                  Корзина
                  {cartCount > 0 && (
                    <span className="ml-1 inline-flex items-center justify-center bg-brand-600 text-white text-xs rounded-full w-5 h-5">
                      {cartCount}
                    </span>
                  )}
                </NavLink>
                <NavLink to="/requests" className={navLinkClass}>
                  Мои заявки
                </NavLink>
                <NavLink to="/proposals" className={navLinkClass}>
                  Мои КП
                </NavLink>
                <NavLink to="/orders" className={navLinkClass}>
                  Мои заказы
                </NavLink>
              </>
            )}

            {isManagerSide && (
              <>
                <NavLink to="/manager/requests" className={navLinkClass}>
                  Заявки
                </NavLink>
                <NavLink to="/proposals" className={navLinkClass}>
                  КП
                </NavLink>
                <NavLink to="/orders" className={navLinkClass}>
                  Заказы
                </NavLink>
                <NavLink to="/admin/parts" className={navLinkClass}>
                  Запчасти
                </NavLink>
                <NavLink to="/admin/categories" className={navLinkClass}>
                  Категории
                </NavLink>
              </>
            )}

            {user?.role === "admin" && (
              <NavLink to="/admin/users" className={navLinkClass}>
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
