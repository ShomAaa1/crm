import { FormEvent, useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { extractError } from "@/api/client";

export function LoginPage() {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  const login = useAuthStore((s) => s.login);

  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;

  const [email, setEmail] = useState("admin@autodetail.ru");
  const [password, setPassword] = useState("Admin123!");
  const [error, setError] = useState<string | null>(null);

  if (user) {
    return <Navigate to={from || defaultRouteFor(user.role)} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await login(email, password);
      const role = useAuthStore.getState().user?.role;
      navigate(from || defaultRouteFor(role), { replace: true });
    } catch (err) {
      setError(extractError(err));
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-100 px-4">
      <div className="card w-full max-w-md p-8">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold text-brand-700">АвтоДеталь CRM</h1>
          <p className="text-slate-500 text-sm mt-1">
            Вход в систему для авторизованных пользователей
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="label">Email</label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              className="input"
            />
          </div>
          <div>
            <label htmlFor="password" className="label">Пароль</label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              className="input"
            />
          </div>

          {error && (
            <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full"
          >
            {loading ? "Входим…" : "Войти"}
          </button>
        </form>

        <div className="mt-6 text-xs text-slate-500">
          <div className="font-medium mb-1">Демо-учётные записи:</div>
          <ul className="space-y-0.5">
            <li>admin@autodetail.ru / Admin123!</li>
            <li>head@autodetail.ru / Head123!</li>
            <li>manager1@autodetail.ru / Manager123!</li>
            <li>client1@autodetail.ru / Client123!</li>
          </ul>
        </div>
      </div>
    </div>
  );
}

function defaultRouteFor(role: string | undefined): string {
  if (role === "admin") return "/admin/users";
  return "/";
}
