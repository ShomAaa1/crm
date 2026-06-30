import { FormEvent, useState } from "react";
import { useNavigate, useLocation, Navigate } from "react-router-dom";
import { useAuthStore } from "@/store/auth";
import { extractError } from "@/api/client";
import { PasswordInput } from "@/components/PasswordInput";

export function LoginPage() {
  const user = useAuthStore((s) => s.user);
  const loading = useAuthStore((s) => s.loading);
  const login = useAuthStore((s) => s.login);

  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: { pathname: string } } | null)?.from?.pathname;

  // В режиме разработки поля предзаполняются для удобства тестирования.
  // В production-сборке поля пустые — устраняется через import.meta.env.DEV.
  const [email, setEmail] = useState(import.meta.env.DEV ? "admin@autodetail.ru" : "");
  const [password, setPassword] = useState(import.meta.env.DEV ? "Admin123!" : "");
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
            <PasswordInput
              id="password"
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

        {/*
          Демонстрационные учётные записи показываются только в режиме
          разработки. В production-сборке (npm run build) Vite вычистит
          этот блок на этапе компиляции, поэтому реальные учётные данные
          не попадут в итоговый bundle.
        */}
        {import.meta.env.DEV && (
          <div className="mt-6 rounded-md border border-amber-200 bg-amber-50 p-3 text-xs text-amber-900">
            <div className="font-semibold mb-1">
              Демонстрационные учётные записи (режим разработки):
            </div>
            <ul className="space-y-0.5 font-mono">
              <li>admin@autodetail.ru / Admin123!</li>
              <li>head@autodetail.ru / Head123!</li>
              <li>manager1@autodetail.ru / Manager123!</li>
              <li>client1@autodetail.ru / Client123!</li>
            </ul>
            <p className="mt-2 italic text-[11px] text-amber-700">
              Блок отображается только в dev-окружении и отсутствует в
              production-сборке.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function defaultRouteFor(role: string | undefined): string {
  if (role === "admin") return "/admin/users";
  return "/";
}
