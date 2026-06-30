import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  assignRequest,
  cancelRequest,
  changeStatus,
  getRequest,
  STATUS_COLOR,
  STATUS_LABEL,
  takeRequest,
} from "@/api/requests";
import {
  createFromRequest,
  getProposalByRequest,
  CP_STATUS_LABEL,
} from "@/api/proposals";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import { AssignManagerModal } from "@/components/AssignManagerModal";
import type {
  CPDetail,
  ClientFinance,
  RequestDetail,
  RequestStatus,
} from "@/types";

// Допустимые переходы — должны совпадать с ALLOWED_TRANSITIONS на бэкенде
const ALLOWED: Record<RequestStatus, RequestStatus[]> = {
  new: ["in_progress", "cancelled"],
  in_progress: ["cp_sent", "revision_needed", "closed_fail"],
  cp_sent: ["accepted", "rejected", "revision_needed"],
  accepted: ["closed_success"],
  rejected: ["closed_fail"],
  revision_needed: ["in_progress", "closed_fail"],
  closed_success: [],
  closed_fail: [],
  cancelled: [],
};

export function RequestDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const navigate = useNavigate();

  const [data, setData] = useState<RequestDetail | null>(null);
  const [proposal, setProposal] = useState<CPDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [showAssign, setShowAssign] = useState(false);

  async function load() {
    if (!id) return;
    setLoading(true);
    setError(null);
    try {
      const r = await getRequest(id);
      setData(r);
      try {
        const cp = await getProposalByRequest(id);
        setProposal(cp);
      } catch {
        setProposal(null);
      }
    } catch (err) {
      setError(extractError(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function action(fn: () => Promise<RequestDetail>) {
    setBusy(true);
    setError(null);
    try {
      const r = await fn();
      setData(r);
    } catch (err) {
      setError(extractError(err));
    } finally {
      setBusy(false);
    }
  }

  if (loading || !data) {
    return <div className="text-slate-500">Загрузка…</div>;
  }

  const isClient = user?.role === "client";
  const isManagerSide =
    user?.role === "manager" || user?.role === "head" || user?.role === "admin";
  const isHeadOrAdmin = user?.role === "head" || user?.role === "admin";

  const isClosed =
    data.status === "closed_success" ||
    data.status === "closed_fail" ||
    data.status === "cancelled";

  // Кнопка «Назначить»/«Переназначить» — для head/admin, на не закрытых заявках
  const canAssign = isHeadOrAdmin && !isClosed;

  async function handleAssign(managerId: string, reason: string) {
    if (!data) return;
    const updated = await assignRequest(data.id, managerId, reason || undefined);
    setData(updated);
    setShowAssign(false);
  }

  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold">
            Заявка{" "}
            <span className="font-mono text-base text-slate-700">
              {data.request_number}
            </span>
          </h2>
          <div className="mt-1 flex items-center gap-2 flex-wrap text-sm">
            <span
              className={`px-2 py-0.5 rounded text-xs ${STATUS_COLOR[data.status]}`}
            >
              {STATUS_LABEL[data.status]}
            </span>
            {data.sla_overdue && (
              <span className="px-2 py-0.5 rounded text-xs bg-red-100 text-red-800">
                SLA просрочен
              </span>
            )}
            <span className="text-slate-500">
              {new Date(data.created_at).toLocaleString("ru-RU")}
            </span>
          </div>
        </div>
        <Link
          to={isClient ? "/requests" : "/manager/requests"}
          className="btn-secondary"
        >
          ← К списку
        </Link>
      </div>

      {error && (
        <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Двухколоночный layout: основная карточка + sticky-sidebar клиента */}
      <div className="grid lg:grid-cols-[1fr_320px] gap-4 items-start">
        {/* === ЛЕВАЯ КОЛОНКА — основная заявка === */}
        <div className="space-y-4 min-w-0">
          <div className="card p-4">
            <div className="text-sm font-medium text-slate-700 mb-2">
              Комментарий клиента
            </div>
            <div className="text-sm text-slate-600 whitespace-pre-wrap">
              {data.comment || <span className="text-slate-400">пусто</span>}
            </div>
            {data.sla_deadline && (
              <div className="mt-3 text-xs text-slate-500">
                SLA до:{" "}
                {new Date(data.sla_deadline).toLocaleString("ru-RU")}
              </div>
            )}
          </div>

          <div className="card overflow-hidden">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-2">Артикул</th>
                  <th className="text-left px-4 py-2">Название</th>
                  <th className="text-right px-4 py-2">Цена</th>
                  <th className="text-center px-4 py-2">Кол-во</th>
                  <th className="text-right px-4 py-2">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((it) => (
                  <tr key={it.id} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-mono text-xs">
                      {it.article || "—"}
                    </td>
                    <td className="px-4 py-2">{it.name || it.description}</td>
                    <td className="px-4 py-2 text-right">
                      {it.price_at_moment ? `${it.price_at_moment} ₽` : "—"}
                    </td>
                    <td className="px-4 py-2 text-center">{it.quantity}</td>
                    <td className="px-4 py-2 text-right font-medium">
                      {it.line_total ? `${it.line_total} ₽` : "—"}
                    </td>
                  </tr>
                ))}
                <tr className="border-t border-slate-200 bg-slate-50">
                  <td colSpan={4} className="px-4 py-2 text-right font-medium">
                    Итого
                  </td>
                  <td className="px-4 py-2 text-right font-semibold">
                    {data.total} ₽
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          {proposal && (
            <div className="card p-4 flex items-center justify-between bg-purple-50/50 border-purple-200">
              <div>
                <div className="text-sm text-slate-600 mb-1">
                  По этой заявке создано КП
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <Link
                    to={`/proposals/${proposal.id}`}
                    className="font-mono text-brand-700 hover:underline"
                  >
                    {proposal.cp_number}
                    {proposal.version > 1 && ` (v${proposal.version})`}
                  </Link>
                  <span className="text-xs text-slate-500">·</span>
                  <span className="text-sm">
                    {CP_STATUS_LABEL[proposal.status]}
                  </span>
                  {proposal.total_amount && (
                    <>
                      <span className="text-xs text-slate-500">·</span>
                      <span className="text-sm font-medium">
                        {proposal.total_amount} ₽
                      </span>
                    </>
                  )}
                </div>
              </div>
              <Link to={`/proposals/${proposal.id}`} className="btn-secondary">
                Открыть КП →
              </Link>
            </div>
          )}

          <div className="card p-4 flex flex-wrap gap-2">
            {isClient && data.status === "new" && (
              <button
                disabled={busy}
                onClick={() => action(() => cancelRequest(data.id))}
                className="btn-danger"
              >
                Отменить заявку
              </button>
            )}

            {isManagerSide && data.status === "new" && !data.manager_id && (
              <button
                disabled={busy}
                onClick={() => action(() => takeRequest(data.id))}
                className="btn-primary"
              >
                Взять в работу
              </button>
            )}

            {isManagerSide &&
              (data.status === "in_progress" ||
                data.status === "revision_needed") &&
              !proposal && (
                <button
                  disabled={busy}
                  onClick={async () => {
                    setBusy(true);
                    setError(null);
                    try {
                      const cp = await createFromRequest(data.id);
                      navigate(`/proposals/${cp.id}`);
                    } catch (err) {
                      setError(extractError(err));
                    } finally {
                      setBusy(false);
                    }
                  }}
                  className="btn-primary"
                >
                  Сформировать КП
                </button>
              )}

            {isManagerSide &&
              ALLOWED[data.status].length > 0 &&
              data.status !== "new" && (
                <StatusActions
                  status={data.status}
                  disabled={busy}
                  onChange={(s) => action(() => changeStatus(data.id, s))}
                />
              )}

            {(data.status === "closed_success" ||
              data.status === "closed_fail" ||
              data.status === "cancelled") && (
              <span className="text-sm text-slate-500 self-center">
                Заявка закрыта{" "}
                {data.closed_at &&
                  `(${new Date(data.closed_at).toLocaleString("ru-RU")})`}
              </span>
            )}
          </div>
        </div>

        {/* === ПРАВАЯ КОЛОНКА — sticky sidebar клиента === */}
        <aside className="lg:sticky lg:top-4 space-y-3">
          <ClientCard
            clientId={data.client_id}
            company={data.client_company}
            managerName={data.manager_name}
            managerId={data.manager_id}
            finance={data.client}
            canAssign={canAssign}
            isManagerSide={isManagerSide}
            onAssignClick={() => setShowAssign(true)}
          />
        </aside>
      </div>

      {showAssign && (
        <AssignManagerModal
          currentManagerId={data.manager_id}
          onCancel={() => setShowAssign(false)}
          onSubmit={handleAssign}
        />
      )}
    </div>
  );
}

function ClientCard({
  clientId,
  company,
  managerName,
  managerId,
  finance,
  canAssign,
  isManagerSide,
  onAssignClick,
}: {
  clientId: string;
  company: string | null;
  managerName: string | null;
  managerId: string | null;
  finance: ClientFinance | null;
  canAssign: boolean;
  isManagerSide: boolean;
  onAssignClick: () => void;
}) {
  return (
    <div className="card p-4 space-y-4">
      <div>
        <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">
          Клиент
        </div>
        <div className="font-semibold text-slate-800 leading-tight">
          {company || "—"}
        </div>
        {isManagerSide && (
          <Link
            to={`/clients/${clientId}`}
            className="text-xs text-brand-700 hover:underline inline-block mt-1"
          >
            История взаимодействия →
          </Link>
        )}
      </div>

      {finance && (
        <>
          <div className="border-t border-slate-100 pt-3 space-y-1.5">
            <Field label="ИНН" value={finance.inn} mono />
            <Field label="КПП" value={finance.kpp} mono />
            {finance.ogrn && <Field label="ОГРН" value={finance.ogrn} mono />}
          </div>

          <div className="border-t border-slate-100 pt-3">
            <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">
              Финансы
            </div>
            <CreditLimitBar
              limit={parseFloat(finance.credit_limit)}
              debt={parseFloat(finance.debt)}
            />
            <DebtBadge debt={parseFloat(finance.debt)} />
          </div>

          {(finance.phone || finance.email) && (
            <div className="border-t border-slate-100 pt-3 space-y-1.5">
              <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">
                Контакты
              </div>
              {finance.phone && (
                <a
                  href={`tel:${finance.phone}`}
                  className="block text-sm text-brand-700 hover:underline"
                >
                  📞 {finance.phone}
                </a>
              )}
              {finance.email && (
                <a
                  href={`mailto:${finance.email}`}
                  className="block text-sm text-brand-700 hover:underline truncate"
                >
                  ✉ {finance.email}
                </a>
              )}
            </div>
          )}
        </>
      )}

      <div className="border-t border-slate-100 pt-3">
        <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">
          Менеджер
        </div>
        <div className="text-sm text-slate-700">
          {managerName || (
            <span className="text-slate-400">не назначен</span>
          )}
        </div>
        {canAssign && (
          <button
            type="button"
            onClick={onAssignClick}
            className="mt-2 w-full text-sm py-1.5 px-3 rounded border border-brand-300 text-brand-700 hover:bg-brand-50 transition-colors"
          >
            {managerId ? "Переназначить" : "Назначить менеджера"}
          </button>
        )}
      </div>
    </div>
  );
}

function Field({
  label,
  value,
  mono,
}: {
  label: string;
  value: string | null;
  mono?: boolean;
}) {
  if (!value) return null;
  return (
    <div className="flex justify-between items-baseline text-sm">
      <span className="text-slate-500">{label}</span>
      <span
        className={`text-slate-800 ${mono ? "font-mono tabular-nums text-xs" : ""}`}
      >
        {value}
      </span>
    </div>
  );
}

function CreditLimitBar({ limit, debt }: { limit: number; debt: number }) {
  if (limit <= 0) {
    return (
      <div className="text-xs text-slate-400 mb-2">
        Кредитный лимит не установлен
      </div>
    );
  }
  const used = Math.min(Math.max(debt, 0), limit);
  const pct = (used / limit) * 100;
  // Цветовая кодировка best-practice
  const color =
    pct >= 80
      ? "bg-red-500"
      : pct >= 50
        ? "bg-amber-500"
        : "bg-emerald-500";
  return (
    <div className="mb-2">
      <div className="flex justify-between text-xs text-slate-500 mb-1">
        <span>Использование лимита</span>
        <span className="tabular-nums">{pct.toFixed(0)}%</span>
      </div>
      <div className="bg-slate-100 rounded h-2 overflow-hidden">
        <div
          className={`h-full ${color} transition-all`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex justify-between text-xs text-slate-500 mt-1 tabular-nums">
        <span>{formatRub(debt)}</span>
        <span>из {formatRub(limit)}</span>
      </div>
    </div>
  );
}

function DebtBadge({ debt }: { debt: number }) {
  if (debt <= 0) {
    return (
      <div className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-emerald-50 text-emerald-700 border border-emerald-200">
        ✓ Долга нет
      </div>
    );
  }
  return (
    <div className="inline-flex items-center gap-1 px-2 py-1 rounded text-xs bg-red-50 text-red-700 border border-red-200">
      ⚠ Долг {formatRub(debt)}
    </div>
  );
}

function formatRub(n: number): string {
  if (!Number.isFinite(n)) return "—";
  return `${n.toLocaleString("ru-RU", { maximumFractionDigits: 0 })} ₽`;
}

function StatusActions({
  status,
  disabled,
  onChange,
}: {
  status: RequestStatus;
  disabled: boolean;
  onChange: (s: RequestStatus) => void;
}) {
  return (
    <>
      {ALLOWED[status].map((s) => (
        <button
          key={s}
          disabled={disabled}
          onClick={() => {
            if (confirm(`Перевести в статус «${STATUS_LABEL[s]}»?`)) {
              onChange(s);
            }
          }}
          className={
            s.startsWith("closed") || s === "rejected"
              ? "btn-secondary"
              : "btn-primary"
          }
        >
          → {STATUS_LABEL[s]}
        </button>
      ))}
    </>
  );
}
