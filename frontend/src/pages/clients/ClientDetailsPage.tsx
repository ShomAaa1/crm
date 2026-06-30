import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ACTIVITY_ICON,
  getClient,
  getClientActivity,
  type ActivityEvent,
  type ClientCard,
  type ClientContactOut,
} from "@/api/clients";
import { extractError } from "@/api/client";
import { useAuthStore } from "@/store/auth";

export function ClientDetailsPage() {
  const { id } = useParams<{ id: string }>();
  const user = useAuthStore((s) => s.user);
  const [client, setClient] = useState<ClientCard | null>(null);
  const [activity, setActivity] = useState<ActivityEvent[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setError(null);
    getClient(id)
      .then(setClient)
      .catch((e) => setError(extractError(e)));
    getClientActivity(id)
      .then(setActivity)
      .catch(() => setActivity([]));
  }, [id]);

  if (error)
    return (
      <div className="rounded-md bg-red-50 border border-red-200 px-3 py-2 text-sm text-red-700">
        {error}
      </div>
    );
  if (!client) return <div className="text-slate-500">Загрузка…</div>;

  const isClient = user?.role === "client";

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold">{client.company_name}</h2>
        <Link to="/manager/requests" className="btn-secondary text-sm">
          ← К заявкам
        </Link>
      </div>

      <div className="grid lg:grid-cols-[1fr_360px] gap-4 items-start">
        {/* Activity timeline */}
        <div className="card p-4">
          <div className="font-medium text-slate-800 mb-3">
            История взаимодействия
          </div>
          {activity === null && (
            <div className="text-slate-500 text-sm">Загрузка…</div>
          )}
          {activity !== null && activity.length === 0 && (
            <div className="text-slate-400 text-sm text-center py-8">
              Пока нет взаимодействий
            </div>
          )}
          {activity !== null && activity.length > 0 && (
            <ol className="relative border-l-2 border-slate-200 ml-3 pl-4 space-y-4">
              {activity.map((e, idx) => (
                <li key={idx} className="relative">
                  <span className="absolute -left-[26px] top-0 inline-flex items-center justify-center w-6 h-6 bg-white border border-slate-200 rounded-full text-sm">
                    {ACTIVITY_ICON[e.kind] || "•"}
                  </span>
                  <div>
                    <div className="text-sm font-medium text-slate-800">
                      {e.title}
                    </div>
                    {e.description && (
                      <div className="mt-0.5 text-xs text-slate-600 whitespace-pre-wrap">
                        {e.description}
                      </div>
                    )}
                    <div className="mt-1 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span>
                        {new Date(e.timestamp).toLocaleString("ru-RU")}
                      </span>
                      {e.actor_name && <span>• {e.actor_name}</span>}
                      {e.amount !== null && (
                        <span className="font-medium">
                          •{" "}
                          {e.amount.toLocaleString("ru-RU", {
                            maximumFractionDigits: 0,
                          })}{" "}
                          ₽
                        </span>
                      )}
                      {e.entity_type === "request" && (
                        <Link
                          to={`/requests/${e.entity_id}`}
                          className="text-brand-700 hover:underline"
                        >
                          → к заявке
                        </Link>
                      )}
                      {e.entity_type === "cp" && (
                        <Link
                          to={`/proposals/${e.entity_id}`}
                          className="text-brand-700 hover:underline"
                        >
                          → к КП
                        </Link>
                      )}
                      {e.entity_type === "order" && (
                        <Link
                          to={`/orders/${e.entity_id}`}
                          className="text-brand-700 hover:underline"
                        >
                          → к заказу
                        </Link>
                      )}
                    </div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>

        {/* Sidebar: реквизиты + контакты */}
        <aside className="lg:sticky lg:top-4 space-y-3">
          <div className="card p-4 space-y-3">
            <div className="text-xs uppercase tracking-wide text-slate-400">
              Реквизиты
            </div>
            <Field label="ИНН" value={client.inn} mono />
            <Field label="КПП" value={client.kpp} mono />
            <Field label="ОГРН" value={client.ogrn} mono />
            {client.legal_address && (
              <div>
                <div className="text-xs text-slate-500 mb-1">Юр. адрес</div>
                <div className="text-sm text-slate-800">
                  {client.legal_address}
                </div>
              </div>
            )}
            {client.delivery_address && (
              <div>
                <div className="text-xs text-slate-500 mb-1">
                  Адрес доставки
                </div>
                <div className="text-sm text-slate-800">
                  {client.delivery_address}
                </div>
              </div>
            )}
          </div>

          {!isClient && (
            <div className="card p-4 space-y-2">
              <div className="text-xs uppercase tracking-wide text-slate-400 mb-2">
                Финансы
              </div>
              <CreditLimitBar
                limit={client.credit_limit}
                debt={client.debt}
              />
              <DebtBadge debt={client.debt} />
            </div>
          )}

          <div className="card p-4 space-y-3">
            <div className="text-xs uppercase tracking-wide text-slate-400">
              Контактные лица ({client.contacts.length})
            </div>
            {client.contacts.length === 0 && (
              <div className="text-slate-400 text-sm">Нет контактов</div>
            )}
            {client.contacts.map((c) => (
              <ContactRow key={c.id} contact={c} />
            ))}
          </div>

          {client.assigned_manager_name && !isClient && (
            <div className="card p-4">
              <div className="text-xs uppercase tracking-wide text-slate-400 mb-1">
                Закреплённый менеджер
              </div>
              <div className="text-sm text-slate-800">
                {client.assigned_manager_name}
              </div>
            </div>
          )}
        </aside>
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

function ContactRow({ contact }: { contact: ClientContactOut }) {
  return (
    <div className="border-t border-slate-100 pt-2 first:border-0 first:pt-0">
      <div className="flex items-center gap-2 flex-wrap">
        <div className="font-medium text-sm text-slate-800">
          {contact.full_name}
        </div>
        {contact.is_primary && (
          <span className="text-xs px-1.5 py-0.5 bg-brand-100 text-brand-700 rounded">
            основной
          </span>
        )}
      </div>
      {contact.position && (
        <div className="text-xs text-slate-500 mt-0.5">{contact.position}</div>
      )}
      <div className="mt-1 space-y-0.5">
        {contact.phone && (
          <a
            href={`tel:${contact.phone}`}
            className="block text-sm text-brand-700 hover:underline"
          >
            📞 {contact.phone}
          </a>
        )}
        {contact.email && (
          <a
            href={`mailto:${contact.email}`}
            className="block text-sm text-brand-700 hover:underline truncate"
          >
            ✉ {contact.email}
          </a>
        )}
      </div>
    </div>
  );
}

function CreditLimitBar({ limit, debt }: { limit: number; debt: number }) {
  if (limit <= 0) {
    return (
      <div className="text-xs text-slate-400">
        Кредитный лимит не установлен
      </div>
    );
  }
  const used = Math.min(Math.max(debt, 0), limit);
  const pct = (used / limit) * 100;
  const color =
    pct >= 80 ? "bg-red-500" : pct >= 50 ? "bg-amber-500" : "bg-emerald-500";
  return (
    <div>
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
