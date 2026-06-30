import { useCallback, useEffect, useState } from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Funnel,
  FunnelChart,
  LabelList,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { getDashboardSummary } from "@/api/dashboard";
import { extractError } from "@/api/client";
import {
  exportOrders,
  exportProposals,
  exportRequests,
} from "@/api/exports";
import { CreateTaskModal } from "@/components/CreateTaskModal";
import { listAvailableManagers } from "@/api/managers";
import type {
  CounterItem,
  DashboardSummary,
  ManagerScore,
  PeriodPreset,
} from "@/types";

type PeriodMode = PeriodPreset | "custom";

const PERIOD_OPTIONS: { value: PeriodMode; label: string }[] = [
  { value: "day", label: "День" },
  { value: "week", label: "Неделя" },
  { value: "month", label: "Месяц" },
  { value: "quarter", label: "Квартал" },
  { value: "year", label: "Год" },
  { value: "custom", label: "Произвольный период" },
];

const FUNNEL_COLORS = ["#2563eb", "#3b82f6", "#60a5fa", "#10b981", "#059669"];

const MONTH_LABELS_RU = [
  "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
  "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек",
];

export function DashboardPage() {
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  // Период
  const [periodMode, setPeriodMode] = useState<PeriodMode>("month");
  const [dateFrom, setDateFrom] = useState<string>("");
  const [dateTo, setDateTo] = useState<string>("");
  // Назначение задачи на менеджера прямо с leaderboard (trigger-based coaching)
  const [taskTarget, setTaskTarget] = useState<{
    managerId: string;
    managerName: string;
  } | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params: Parameters<typeof getDashboardSummary>[0] = {};
      if (periodMode === "custom") {
        if (dateFrom) params.date_from = dateFrom;
        if (dateTo) params.date_to = dateTo;
      } else {
        params.period = periodMode;
      }
      const summary = await getDashboardSummary(params);
      setData(summary);
    } catch (e) {
      setError(extractError(e));
    } finally {
      setLoading(false);
    }
  }, [periodMode, dateFrom, dateTo]);

  useEffect(() => {
    // Для пресетов перезагружаем сразу; для custom — по кнопке «Применить»
    if (periodMode !== "custom") reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [periodMode]);

  useEffect(() => {
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function openTaskFor(managerName: string) {
    // По имени из leaderboard находим manager_id через /managers/available
    try {
      const list = await listAvailableManagers();
      const found = list.find((m) => m.full_name === managerName);
      if (found) {
        setTaskTarget({ managerId: found.id, managerName });
      } else {
        alert("Менеджер не найден в списке доступных");
      }
    } catch (e) {
      alert(extractError(e));
    }
  }

  if (!data && loading) return <div className="text-slate-500">Загрузка…</div>;
  if (!data) {
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
        {error || "Нет данных"}
      </div>
    );
  }

  // Тренд: текущий и предыдущий период на одном графике
  const revenueTrend = data.revenue_by_day.map((p, idx) => ({
    date: p.date.slice(5),
    current: p.value,
    previous: data.previous_revenue_by_day[idx]?.value ?? 0,
  }));

  // Конверсия по месяцам
  const conversionData = data.conversion_by_month.map((p) => {
    const [y, m] = p.month.split("-");
    return {
      month: `${MONTH_LABELS_RU[parseInt(m, 10) - 1]} ${y.slice(2)}`,
      conversion: p.conversion,
    };
  });

  // Воронка
  const funnelData = data.sales_funnel.map((s, i) => ({
    ...s,
    fill: FUNNEL_COLORS[i % FUNNEL_COLORS.length],
  }));

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h2 className="text-xl font-semibold">Дашборд</h2>
          <div className="text-xs text-slate-500 mt-0.5">
            {data.period_label}
            {error && <span className="ml-2 text-red-600">· {error}</span>}
          </div>
        </div>
        <div className="flex gap-2 text-sm">
          <button onClick={exportRequests} className="btn-secondary">
            📊 Заявки
          </button>
          <button onClick={exportProposals} className="btn-secondary">
            📊 КП
          </button>
          <button onClick={exportOrders} className="btn-secondary">
            📊 Заказы
          </button>
        </div>
      </div>

      {/* Селектор периода */}
      <div className="card p-3 flex flex-wrap items-center gap-3">
        <div className="flex gap-1 flex-wrap">
          {PERIOD_OPTIONS.map((o) => (
            <button
              key={o.value}
              onClick={() => setPeriodMode(o.value)}
              className={`px-3 py-1.5 rounded text-sm ${
                periodMode === o.value
                  ? "bg-brand-600 text-white"
                  : "bg-slate-100 text-slate-700 hover:bg-slate-200"
              }`}
            >
              {o.label}
            </button>
          ))}
        </div>
        {periodMode === "custom" && (
          <div className="flex items-center gap-2 ml-auto">
            <input
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
              className="input text-sm"
              max={dateTo || undefined}
            />
            <span className="text-slate-400 text-sm">—</span>
            <input
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
              className="input text-sm"
              min={dateFrom || undefined}
            />
            <button
              onClick={reload}
              disabled={loading || (!dateFrom && !dateTo)}
              className="btn-primary text-sm"
            >
              Применить
            </button>
          </div>
        )}
      </div>

      {/* KPI scorecards с дельтой к предыдущему периоду */}
      <div className="grid md:grid-cols-4 gap-4">
        <KpiCard
          label={`Выручка (${data.period_label.toLowerCase()})`}
          value={`${formatMoney(data.revenue_period)} ₽`}
          delta={data.revenue_delta_pct}
        />
        <KpiCard
          label="Конверсия КП"
          value={`${data.cp_conversion}%`}
          delta={data.conversion_delta_pct}
        />
        <KpiCard
          label="Средний чек"
          value={`${formatMoney(data.avg_deal_size)} ₽`}
          delta={data.avg_deal_size_delta_pct}
        />
        <KpiCard
          label="Сделок закрыто"
          value={String(data.deals_won)}
          delta={data.deals_won_delta_pct}
        />
      </div>

      {/* Дополнительный ряд "операционных" KPI без дельт */}
      <div className="grid md:grid-cols-3 gap-4">
        <KpiCard label="Активные заявки" value={String(data.active_requests)} />
        <KpiCard label="Клиентов" value={String(data.total_clients)} />
        <KpiCard label="Менеджеров" value={String(data.total_managers)} />
      </div>

      {/* Тренд: текущий vs предыдущий период */}
      <ChartCard
        title={`Динамика выручки: текущий период (${data.period_days} дн.) vs предыдущий`}
      >
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart
            data={revenueTrend}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
          >
            <defs>
              <linearGradient id="curGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#2563eb" stopOpacity={0.4} />
                <stop offset="100%" stopColor="#2563eb" stopOpacity={0} />
              </linearGradient>
              <linearGradient id="prevGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#94a3b8" stopOpacity={0.25} />
                <stop offset="100%" stopColor="#94a3b8" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="date" tick={{ fontSize: 11 }} interval={2} />
            <YAxis tick={{ fontSize: 11 }} />
            <Tooltip
              formatter={(v: number, name: string) => [
                `${v.toLocaleString("ru-RU")} ₽`,
                name,
              ]}
            />
            <Legend wrapperStyle={{ fontSize: 12 }} />
            <Area
              type="monotone"
              dataKey="previous"
              name="Прошлый период"
              stroke="#94a3b8"
              strokeDasharray="4 4"
              strokeWidth={1.5}
              fill="url(#prevGrad)"
            />
            <Area
              type="monotone"
              dataKey="current"
              name="Текущий период"
              stroke="#2563eb"
              strokeWidth={2}
              fill="url(#curGrad)"
            />
          </AreaChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Воронка + Leaderboard в один ряд */}
      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="Воронка продаж">
          {funnelData.every((s) => s.value === 0) ? (
            <EmptyHint text="Пока нет заявок" />
          ) : (
            <>
              <ResponsiveContainer width="100%" height={300}>
                <FunnelChart>
                  <Tooltip />
                  <Funnel dataKey="value" data={funnelData} isAnimationActive>
                    <LabelList
                      position="right"
                      dataKey="stage"
                      fill="#334155"
                      stroke="none"
                      fontSize={13}
                    />
                    <LabelList
                      position="center"
                      dataKey="value"
                      fill="#fff"
                      stroke="none"
                      fontSize={14}
                      fontWeight={600}
                    />
                  </Funnel>
                </FunnelChart>
              </ResponsiveContainer>
              <div className="mt-2 space-y-1 text-xs text-slate-500">
                {funnelData.slice(1).map((s) => (
                  <div key={s.stage} className="flex justify-between">
                    <span>↓ {s.stage}</span>
                    <span className="tabular-nums">
                      {s.conversion_pct !== null
                        ? `${s.conversion_pct}%`
                        : "—"}
                    </span>
                  </div>
                ))}
              </div>
            </>
          )}
        </ChartCard>

        <ChartCard title={`Лучшие менеджеры (${data.period_label.toLowerCase()})`}>
          <ManagerLeaderboard
            items={data.manager_leaderboard}
            onAssignTask={openTaskFor}
          />
        </ChartCard>
      </div>

      {/* Ranked lists */}
      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="Заявки по статусам">
          <RankedBars items={data.requests_by_status} accent="#2563eb" />
        </ChartCard>
        <ChartCard title="Заказы по статусам">
          <RankedBars items={data.orders_by_status} accent="#10b981" />
        </ChartCard>
      </div>

      {/* Конверсия по месяцам */}
      <ChartCard title="Конверсия КП по месяцам">
        <ResponsiveContainer width="100%" height={260}>
          <BarChart
            data={conversionData}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="month" tick={{ fontSize: 11 }} />
            <YAxis
              tick={{ fontSize: 11 }}
              domain={[0, 100]}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip formatter={(v: number) => `${v}%`} />
            <Bar
              dataKey="conversion"
              name="Конверсия"
              fill="#8b5cf6"
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {taskTarget && (
        <CreateTaskModal
          presetManagerId={taskTarget.managerId}
          presetManagerName={taskTarget.managerName}
          onCancel={() => setTaskTarget(null)}
          onCreated={() => setTaskTarget(null)}
        />
      )}
    </div>
  );
}

function formatMoney(s: string): string {
  const num = parseFloat(s);
  if (Number.isNaN(num)) return s;
  return num.toLocaleString("ru-RU", { maximumFractionDigits: 0 });
}

function KpiCard({
  label,
  value,
  delta,
}: {
  label: string;
  value: string;
  delta?: number | null;
}) {
  return (
    <div className="card p-4">
      <div className="text-xs text-slate-500 mb-1">{label}</div>
      <div className="text-2xl font-semibold text-brand-700">{value}</div>
      {delta !== undefined && <DeltaBadge delta={delta} />}
    </div>
  );
}

function DeltaBadge({ delta }: { delta: number | null }) {
  if (delta === null) {
    return (
      <div className="text-xs text-slate-400 mt-1">
        нет данных за прошлый период
      </div>
    );
  }
  const isUp = delta > 0;
  const isDown = delta < 0;
  const color = isUp
    ? "text-emerald-600"
    : isDown
      ? "text-red-600"
      : "text-slate-500";
  const arrow = isUp ? "↑" : isDown ? "↓" : "→";
  const sign = delta > 0 ? "+" : "";
  return (
    <div className={`text-xs mt-1 ${color}`}>
      {arrow} {sign}
      {delta}% к прошлому периоду
    </div>
  );
}

function ChartCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card p-4">
      <div className="font-medium text-slate-800 mb-3">{title}</div>
      {children}
    </div>
  );
}

function ManagerLeaderboard({
  items,
  onAssignTask,
}: {
  items: ManagerScore[];
  onAssignTask?: (managerName: string) => void;
}) {
  if (items.length === 0) return <EmptyHint text="Нет данных по менеджерам" />;
  const max = Math.max(...items.map((i) => i.revenue), 1);
  return (
    <div className="space-y-3">
      {items.map((m, idx) => {
        const width = (m.revenue / max) * 100;
        const medal = ["🥇", "🥈", "🥉"][idx] ?? `${idx + 1}.`;
        return (
          <div key={m.manager_name} className="group">
            <div className="flex justify-between text-sm mb-1 items-baseline gap-2">
              <span className="text-slate-700 min-w-0 truncate">
                <span className="mr-2">{medal}</span>
                {m.manager_name}
              </span>
              <span className="tabular-nums flex items-center gap-2 shrink-0">
                <span className="font-semibold">
                  {m.revenue.toLocaleString("ru-RU", {
                    maximumFractionDigits: 0,
                  })}{" "}
                  ₽
                </span>
                <span className="text-slate-400 text-xs">
                  {m.deals_count} сделок
                </span>
                {onAssignTask && (
                  <button
                    onClick={() => onAssignTask(m.manager_name)}
                    title="Поставить задачу этому менеджеру"
                    className="opacity-0 group-hover:opacity-100 transition-opacity text-xs px-1.5 py-0.5 rounded border border-brand-300 text-brand-700 hover:bg-brand-50"
                  >
                    + задача
                  </button>
                )}
              </span>
            </div>
            <div className="bg-slate-100 rounded h-1.5 overflow-hidden">
              <div
                className="h-full bg-brand-500 transition-all"
                style={{ width: `${width}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function RankedBars({
  items,
  accent,
}: {
  items: CounterItem[];
  accent: string;
}) {
  const total = items.reduce((acc, it) => acc + it.value, 0);
  const max = Math.max(...items.map((i) => i.value), 1);
  if (total === 0) return <EmptyHint text="Пока нет данных" />;
  const sorted = [...items].sort((a, b) => b.value - a.value);
  return (
    <div className="space-y-2.5">
      {sorted.map((it) => {
        const pct = total > 0 ? (it.value / total) * 100 : 0;
        const width = (it.value / max) * 100;
        return (
          <div key={it.label}>
            <div className="flex justify-between text-sm mb-1">
              <span className="text-slate-600">{it.label}</span>
              <span className="font-medium tabular-nums">
                {it.value}
                <span className="text-slate-400 text-xs ml-1">
                  ({pct.toFixed(0)}%)
                </span>
              </span>
            </div>
            <div className="bg-slate-100 rounded h-1.5 overflow-hidden">
              <div
                className="h-full transition-all"
                style={{ width: `${width}%`, backgroundColor: accent }}
              />
            </div>
          </div>
        );
      })}
      <div className="pt-2 border-t border-slate-100 flex justify-between text-xs text-slate-500">
        <span>Всего</span>
        <span className="font-medium text-slate-700 tabular-nums">{total}</span>
      </div>
    </div>
  );
}

function EmptyHint({ text }: { text: string }) {
  return (
    <div className="text-slate-400 text-sm text-center py-10">{text}</div>
  );
}
