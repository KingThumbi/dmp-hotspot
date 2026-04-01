import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiGetWithAuth } from "../../lib/api";
import { formatDateTime } from "../../utils/format";

type ReminderItem = {
  id: number;
  customer_id: number;
  customer_name: string;
  account_number: string | null;
  subscription_id: number;
  service_type: string | null;
  expires_at: string | null;
  channel: string;
  reminder_type: string;
  phone: string | null;
  recipient_name: string | null;
  message_body: string | null;
  status: string;
  provider: string | null;
  provider_message_id: string | null;
  error_message: string | null;
  sent_at: string | null;
  created_at: string | null;
};

type ReminderSummary = {
  total: number;
  sent: number;
  failed: number;
  skipped: number;
  sms: number;
  whatsapp: number;
  by_type: Record<string, number>;
};

function statusTone(status: string) {
  switch (status) {
    case "sent":
      return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    case "failed":
      return "bg-red-50 text-red-700 ring-red-200";
    case "skipped":
      return "bg-amber-50 text-amber-700 ring-amber-200";
    default:
      return "bg-slate-50 text-slate-700 ring-slate-200";
  }
}

function channelTone(channel: string) {
  switch (channel) {
    case "sms":
      return "bg-blue-50 text-blue-700 ring-blue-200";
    case "whatsapp":
      return "bg-green-50 text-green-700 ring-green-200";
    default:
      return "bg-slate-50 text-slate-700 ring-slate-200";
  }
}

function reminderLabel(value: string) {
  switch (value) {
    case "days_before_2":
      return "2 Days Before";
    case "days_before_1":
      return "1 Day Before";
    case "on_disconnect":
      return "On Disconnect";
    default:
      return value;
  }
}

function canResend(status: string) {
  return status === "failed" || status === "skipped";
}

function StatCard({
  label,
  value,
  helper,
}: {
  label: string;
  value: number | string;
  helper?: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold text-slate-900">{value}</div>
      {helper ? <div className="mt-1 text-sm text-slate-500">{helper}</div> : null}
    </div>
  );
}

export default function RenewalReminders() {
  const [items, setItems] = useState<ReminderItem[]>([]);
  const [summary, setSummary] = useState<ReminderSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [resendingId, setResendingId] = useState<number | null>(null);

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [channel, setChannel] = useState("");
  const [reminderType, setReminderType] = useState("");

  async function loadData() {
    setLoading(true);

    try {
      const params = new URLSearchParams();

      if (q.trim()) params.set("q", q.trim());
      if (status) params.set("status", status);
      if (channel) params.set("channel", channel);
      if (reminderType) params.set("reminder_type", reminderType);

      params.set("limit", "150");

      const [itemsRes, summaryRes] = await Promise.all([
        apiGetWithAuth(`/api/admin/reminders?${params.toString()}`),
        apiGetWithAuth("/api/admin/reminders/summary"),
      ]);

      setItems(itemsRes.items || []);
      setSummary(summaryRes.summary || null);
    } finally {
      setLoading(false);
    }
  }

  async function handleResend(item: ReminderItem) {
    try {
      setResendingId(item.id);

      // Wire this to your backend resend endpoint when ready.
      // Example:
      // await apiPostWithAuth(`/api/admin/reminders/${item.id}/resend`, {});
      console.log("Resend reminder:", item.id, item);

      await loadData();
    } catch (error) {
      console.error("Failed to resend reminder", error);
    } finally {
      setResendingId(null);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const filteredCount = useMemo(() => items.length, [items]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Renewal Reminders
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Monitor 2-day, 1-day, and disconnect reminder delivery across SMS
              and WhatsApp.
            </p>
          </div>

          <button
            onClick={() => void loadData()}
            className="inline-flex h-11 items-center justify-center rounded-xl bg-slate-900 px-4 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
          >
            Refresh
          </button>
        </div>
      </div>

      {/* Summary cards */}
      {summary ? (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <StatCard label="Total" value={summary.total} />
          <StatCard label="Sent" value={summary.sent} />
          <StatCard label="Failed" value={summary.failed} />
          <StatCard label="Skipped" value={summary.skipped} />
          <StatCard label="SMS" value={summary.sms} />
          <StatCard label="WhatsApp" value={summary.whatsapp} />
        </div>
      ) : null}

      {/* Filters */}
      <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search customer, phone, account..."
            className="h-11 rounded-xl border border-slate-200 px-3 text-sm outline-none ring-0 placeholder:text-slate-400 focus:border-slate-400"
          />

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="h-11 rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Statuses</option>
            <option value="sent">Sent</option>
            <option value="failed">Failed</option>
            <option value="skipped">Skipped</option>
          </select>

          <select
            value={channel}
            onChange={(e) => setChannel(e.target.value)}
            className="h-11 rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Channels</option>
            <option value="sms">SMS</option>
            <option value="whatsapp">WhatsApp</option>
          </select>

          <select
            value={reminderType}
            onChange={(e) => setReminderType(e.target.value)}
            className="h-11 rounded-xl border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Reminder Types</option>
            <option value="days_before_2">2 Days Before</option>
            <option value="days_before_1">1 Day Before</option>
            <option value="on_disconnect">On Disconnect</option>
          </select>

          <button
            onClick={() => void loadData()}
            className="h-11 rounded-xl bg-amber-500 px-4 text-sm font-semibold text-slate-950 shadow-sm transition hover:opacity-90"
          >
            Apply Filters
          </button>
        </div>

        <div className="mt-3 text-sm text-slate-500">
          Showing {filteredCount} reminder record
          {filteredCount === 1 ? "" : "s"}.
        </div>
      </div>

      {/* Reminder log table */}
      <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-semibold">Customer</th>
                <th className="px-4 py-3 font-semibold">Account</th>
                <th className="px-4 py-3 font-semibold">Service</th>
                <th className="px-4 py-3 font-semibold">Channel</th>
                <th className="px-4 py-3 font-semibold">Reminder</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Expires</th>
                <th className="px-4 py-3 font-semibold">Sent</th>
                <th className="px-4 py-3 font-semibold">Error</th>
                <th className="px-4 py-3 font-semibold">Actions</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-4 py-10 text-center text-slate-500"
                  >
                    Loading reminders...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td
                    colSpan={10}
                    className="px-4 py-10 text-center text-slate-500"
                  >
                    No reminder records found.
                  </td>
                </tr>
              ) : (
                items.map((item) => (
                  <tr key={item.id} className="align-top">
                    {/* Customer quick navigation */}
                    <td className="px-4 py-4">
                      <Link
                        to={`/admin-ui/customers/${item.customer_id}`}
                        className="inline-flex items-center gap-2 font-semibold text-[var(--navy)] transition hover:underline"
                        title={`Open ${item.customer_name}`}
                      >
                        {item.customer_name}
                      </Link>

                      <div className="text-xs text-slate-500">
                        {item.phone || "No phone"}
                      </div>
                    </td>

                    {/* Account quick navigation */}
                    <td className="px-4 py-4">
                      {item.account_number ? (
                        <Link
                          to={`/admin-ui/customers/${item.customer_id}`}
                          className="font-semibold text-slate-900 transition hover:underline"
                          title={`Open account ${item.account_number}`}
                        >
                          {item.account_number}
                        </Link>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>

                    <td className="px-4 py-4 text-slate-700">
                      {item.service_type || "—"}
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${channelTone(
                          item.channel
                        )}`}
                      >
                        {item.channel}
                      </span>
                    </td>

                    <td className="px-4 py-4 text-slate-700">
                      {reminderLabel(item.reminder_type)}
                    </td>

                    <td className="px-4 py-4">
                      <span
                        className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ring-1 ${statusTone(
                          item.status
                        )}`}
                      >
                        {item.status}
                      </span>
                    </td>

                    <td className="px-4 py-4 text-slate-700">
                      {item.expires_at ? formatDateTime(item.expires_at) : "—"}
                    </td>

                    <td className="px-4 py-4 text-slate-700">
                      {item.sent_at ? formatDateTime(item.sent_at) : "—"}
                    </td>

                    <td className="px-4 py-4">
                      {item.error_message ? (
                        <div className="max-w-xs text-xs text-red-600">
                          {item.error_message}
                        </div>
                      ) : (
                        <span className="text-slate-400">—</span>
                      )}
                    </td>

                    <td className="px-4 py-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Link
                          to={`/admin-ui/customers/${item.customer_id}`}
                          className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                          title={`View ${item.customer_name}`}
                        >
                          View Customer
                        </Link>

                        {canResend(item.status) ? (
                          <button
                            type="button"
                            onClick={() => void handleResend(item)}
                            disabled={resendingId === item.id}
                            className="inline-flex h-9 items-center justify-center rounded-lg bg-amber-500 px-3 text-xs font-semibold text-slate-950 shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-60"
                            title={`Resend ${reminderLabel(item.reminder_type)} reminder`}
                          >
                            {resendingId === item.id ? "Resending..." : "Resend"}
                          </button>
                        ) : null}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Reminder type totals */}
      {summary?.by_type ? (
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            label="2 Days Before"
            value={summary.by_type.days_before_2 || 0}
          />
          <StatCard
            label="1 Day Before"
            value={summary.by_type.days_before_1 || 0}
          />
          <StatCard
            label="On Disconnect"
            value={summary.by_type.on_disconnect || 0}
          />
        </div>
      ) : null}
    </div>
  );
}