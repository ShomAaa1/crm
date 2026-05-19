import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getNotifications,
  markAllRead,
  markRead,
  relatedLink,
} from "@/api/notifications";
import { extractError } from "@/api/client";
import type { NotificationItem, NotificationSummary } from "@/types";

const POLL_INTERVAL_MS = 15000;

export function NotificationsBell() {
  const [data, setData] = useState<NotificationSummary | null>(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dropdownRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();

  async function refresh() {
    try {
      const d = await getNotifications(false, 20);
      setData(d);
    } catch (err) {
      setError(extractError(err));
    }
  }

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, POLL_INTERVAL_MS);
    return () => clearInterval(id);
  }, []);

  // Закрытие по клику вне
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!dropdownRef.current) return;
      if (!dropdownRef.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, []);

  async function onItemClick(n: NotificationItem) {
    setOpen(false);
    if (!n.is_read) {
      try {
        await markRead(n.id);
        await refresh();
      } catch {
        // ignore
      }
    }
    const link = relatedLink(n);
    if (link) navigate(link);
  }

  async function onMarkAll() {
    await markAllRead();
    await refresh();
  }

  const unread = data?.unread_count ?? 0;

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 text-slate-600 hover:text-brand-700"
        aria-label="Уведомления"
      >
        <BellIcon />
        {unread > 0 && (
          <span className="absolute top-0 right-0 inline-flex items-center justify-center bg-red-600 text-white text-[10px] rounded-full w-5 h-5">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-96 card overflow-hidden z-20 shadow-lg">
          <div className="flex items-center justify-between px-4 py-2 border-b bg-slate-50">
            <div className="font-medium text-sm">Уведомления</div>
            {unread > 0 && (
              <button
                onClick={onMarkAll}
                className="text-xs text-brand-700 hover:underline"
              >
                Отметить все прочитанными
              </button>
            )}
          </div>
          {error && (
            <div className="px-4 py-2 text-xs text-red-700">{error}</div>
          )}
          <div className="max-h-96 overflow-auto">
            {!data || data.items.length === 0 ? (
              <div className="px-4 py-8 text-center text-slate-500 text-sm">
                Уведомлений пока нет
              </div>
            ) : (
              data.items.map((n) => (
                <button
                  key={n.id}
                  onClick={() => onItemClick(n)}
                  className={`w-full text-left px-4 py-3 border-b border-slate-100 hover:bg-slate-50 ${
                    n.is_read ? "" : "bg-blue-50/50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="font-medium text-sm">{n.title}</div>
                    {!n.is_read && (
                      <span className="mt-1 w-2 h-2 rounded-full bg-brand-600 flex-shrink-0" />
                    )}
                  </div>
                  {n.message && (
                    <div className="text-xs text-slate-600 mt-1">{n.message}</div>
                  )}
                  <div className="text-xs text-slate-400 mt-1">
                    {new Date(n.created_at).toLocaleString("ru-RU")}
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

function BellIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
    </svg>
  );
}
