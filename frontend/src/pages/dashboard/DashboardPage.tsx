import { useEffect, useState } from "react";
import { getDashboardSummary } from "@/api/dashboard";
import { extractError } from "@/api/client";
import type { DashboardSummary } from "@/types";

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboardSummary()
      .then(setData)
      .catch((e) => setError(extractError(e)));
  }, []);

  if (error)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
        {error}
      </div>
    );
  if (!data) return <div className="text-slate-500">Загрузка…</div>;

  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold">Дашборд</h2>

      <div className="grid md:grid-cols-4 gap-4">
        <KpiCard label="Выручка за 30 дней" value={`${data.revenue_30d} ₽`} />
        <KpiCard label="Конверсия КП" value={`${data.cp_conversion}%`} />
        <KpiCard label="Клиентов" value={String(data.total_clients)} />
        <KpiCard label="Менеджеров" value={String(data.total_managers)} />
      </div>

      <div className="grid md:grid-cols-3 gap-4">
        <CounterCard title="Заявки по статусам" items={data.requests_by_status} />
        <CounterCard title="КП по статусам" items={data.proposals_by_status} />
        <CounterCard title="Заказы по статусам" items={data.orders_by_status} />
      </div>
    </div>
  );
}

function KpiCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="card p-4">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold text-brand-700">{value}</div>
    </div>
  );
}

function CounterCard({
  title,
  items,
}: {
  title: string;
  items: { label: string; value: number }[];
}) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="card p-4">
      <div className="font-medium text-slate-800 mb-3">{title}</div>
      <div className="space-y-2">
        {items.map((it) => (
          <div key={it.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-600">{it.label}</span>
              <span className="font-medium">{it.value}</span>
            </div>
            <div className="bg-slate-100 rounded h-1.5 overflow-hidden">
              <div
                className="bg-brand-500 h-full"
                style={{ width: `${(it.value / max) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
