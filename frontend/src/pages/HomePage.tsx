import { useAuthStore } from "@/store/auth";

export function HomePage() {
  const user = useAuthStore((s) => s.user);

  return (
    <div className="card p-6 max-w-2xl">
      <h2 className="text-xl font-semibold mb-2">
        Здравствуйте, {user?.full_name}!
      </h2>
      <p className="text-slate-600">
        Добро пожаловать в АвтоДеталь CRM. Используйте меню сверху для навигации.
      </p>
      <div className="mt-4 text-sm text-slate-500">
        <div>Email: {user?.email}</div>
        <div>Роль: {user?.role}</div>
      </div>
    </div>
  );
}
