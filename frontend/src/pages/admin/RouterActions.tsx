import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";

import { apiGetWithAuth } from "../../lib/api";
import { adminLoginUrl } from "../../lib/adminAuth";
import { formatDateTime } from "../../utils/format";

type RouterAction = {
  id: number;
  action_key: string;
  status: string;
  action_type: string;
  service_type: string | null;
  subscription_id: number | null;
  customer_id: number | null;
  package_id: number | null;
  router_id: number | null;
  identity: string | null;
  profile_name: string | null;
  priority: number;
  attempt_count: number;
  max_attempts: number;
  next_run_at: string | null;
  locked_at: string | null;
  locked_by: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_by: string | null;
  created_by_admin_id: number | null;
  correlation_id: string | null;
  error_message: string | null;
  payload_json: string | null;
  result_json: string | null;
  created_at: string | null;
  updated_at: string | null;
  age_minutes: number | null;
  is_stale: boolean;
};

type RouterActionsResponse = {
  ok: boolean;
  data: RouterAction[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
};

type RouterActionsSummaryResponse = {
  ok: boolean;
  summary: {
    total: number;
    by_status: Record<string, number>;
    by_action_type: Record<string, number>;
    health?: {
      stale_after_minutes: number;
      queued_total: number;
      retrying_total: number;
      failed_total: number;
      queued_reconnects: number;
      queued_disconnects: number;
      stale_queued: number;
      missing_subscription_links: number;
      failed_disconnects: number;
      malformed_payloads_sample: number;
      payload_sample_size: number;
      oldest_queued_created_at: string | null;
      oldest_queued_age_minutes: number | null;
      newest_queued_created_at: string | null;
      newest_queued_age_minutes: number | null;
      average_queued_age_minutes: number;
      repeated_disconnects: Array<{
        subscription_id: number | null;
        identity: string | null;
        count: number;
      }>;
      duplicate_detection: {
        stored_action_keys: number;
        duplicate_action_key_hits_since_start: number;
      };
      enqueue_metrics: {
        attempts: number;
        created: number;
        duplicate_action_key_hits: number;
        failures: number;
        failures_by_action_type: Record<string, number>;
      };
      warnings: Array<{
        level: string;
        code: string;
        message: string;
        count: number | null;
      }>;
    };
  };
};

function statusTone(status: string) {
  switch ((status || "").toLowerCase()) {
    case "queued":
      return "bg-blue-50 text-blue-700 ring-blue-200";
    case "retrying":
      return "bg-amber-50 text-amber-700 ring-amber-200";
    case "failed":
      return "bg-red-50 text-red-700 ring-red-200";
    case "succeeded":
      return "bg-emerald-50 text-emerald-700 ring-emerald-200";
    case "processing":
      return "bg-violet-50 text-violet-700 ring-violet-200";
    default:
      return "bg-slate-50 text-slate-700 ring-slate-200";
  }
}

function actionLabel(actionType: string) {
  return actionType.replace(/^subscription\./, "").replaceAll("_", " ");
}

function parsePayload(item: RouterAction): Record<string, unknown> {
  if (!item.payload_json) return {};
  try {
    const parsed = JSON.parse(item.payload_json);
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
}

function hasMalformedPayload(item: RouterAction) {
  if (!item.payload_json) return false;
  try {
    const parsed = JSON.parse(item.payload_json);
    return !(parsed && typeof parsed === "object");
  } catch {
    return true;
  }
}

function isPastDate(value: unknown) {
  if (!value || typeof value !== "string") return false;
  const date = new Date(value);
  return !Number.isNaN(date.getTime()) && date.getTime() < Date.now();
}

function actionFlags(item: RouterAction) {
  const payload = parsePayload(item);
  const reason = String(payload.reason || "").toLowerCase();
  const createdBy = (item.created_by || "").toLowerCase();
  const actionType = (item.action_type || "").toLowerCase();
  const status = (item.status || "").toLowerCase();
  const payloadStatus = String(payload.status || "").toLowerCase();

  return {
    expiredReconnectQueued:
      status === "queued" &&
      actionType.includes("reconnect") &&
      (payloadStatus === "expired" || isPastDate(payload.expires_at)),
    reconnectAfterPayment:
      actionType.includes("reconnect") &&
      (reason.includes("payment") ||
        createdBy.includes("payment") ||
        createdBy.includes("mpesa")),
    failedDisconnect:
      actionType.includes("disconnect") &&
      (status === "failed" || status === "retrying" || Boolean(item.error_message)),
    staleQueued: Boolean(item.is_stale),
    malformedPayload: hasMalformedPayload(item),
    missingSubscriptionLink: item.subscription_id === null || item.subscription_id === undefined,
  };
}

function StatCard({
  label,
  value,
  helper,
  tone = "slate",
}: {
  label: string;
  value: number | string;
  helper?: string;
  tone?: "slate" | "blue" | "amber" | "red" | "emerald";
}) {
  const toneClass = {
    slate: "border-slate-200 bg-white text-slate-900",
    blue: "border-blue-200 bg-blue-50 text-blue-950",
    amber: "border-amber-200 bg-amber-50 text-amber-950",
    red: "border-red-200 bg-red-50 text-red-950",
    emerald: "border-emerald-200 bg-emerald-50 text-emerald-950",
  }[tone];

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClass}`}>
      <div className="text-xs font-semibold uppercase text-slate-500">
        {label}
      </div>
      <div className="mt-2 text-3xl font-bold">{value}</div>
      {helper ? <div className="mt-1 text-sm text-slate-500">{helper}</div> : null}
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: unknown }) {
  return (
    <div className="grid gap-1 border-b border-slate-100 py-3 md:grid-cols-3">
      <div className="text-xs font-semibold uppercase text-slate-500">{label}</div>
      <div className="break-words text-sm text-slate-900 md:col-span-2">
        {value === null || value === undefined || value === "" ? "—" : String(value)}
      </div>
    </div>
  );
}

function DetailModal({
  item,
  onClose,
}: {
  item: RouterAction;
  onClose: () => void;
}) {
  const payload = parsePayload(item);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div className="max-h-[88vh] w-full max-w-4xl overflow-hidden rounded-lg bg-white shadow-xl">
        <div className="flex items-start justify-between gap-4 border-b border-slate-200 p-5">
          <div>
            <div className="text-sm font-semibold text-slate-500">
              Router Action #{item.id}
            </div>
            <h2 className="mt-1 text-xl font-bold text-slate-950">
              {actionLabel(item.action_type)}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-sm font-semibold text-slate-700 shadow-sm transition hover:bg-slate-50"
          >
            Close
          </button>
        </div>

        <div className="max-h-[70vh] overflow-y-auto p-5">
          <div className="grid gap-4 lg:grid-cols-2">
            <div>
              <DetailRow label="Status" value={item.status} />
              <DetailRow label="Action Type" value={item.action_type} />
              <DetailRow label="Service Type" value={item.service_type} />
              <DetailRow label="Identity" value={item.identity} />
              <DetailRow label="Profile" value={item.profile_name} />
              <DetailRow label="Subscription" value={item.subscription_id} />
              <DetailRow label="Customer" value={item.customer_id} />
              <DetailRow label="Created By" value={item.created_by} />
            </div>

            <div>
              <DetailRow label="Action Key" value={item.action_key} />
              <DetailRow label="Correlation" value={item.correlation_id} />
              <DetailRow label="Priority" value={item.priority} />
              <DetailRow
                label="Attempts"
                value={`${item.attempt_count} / ${item.max_attempts}`}
              />
              <DetailRow label="Next Run" value={formatDateTime(item.next_run_at)} />
              <DetailRow label="Created" value={formatDateTime(item.created_at)} />
              <DetailRow
                label="Queue Age"
                value={item.age_minutes === null ? "—" : `${item.age_minutes} min`}
              />
              <DetailRow label="Updated" value={formatDateTime(item.updated_at)} />
              <DetailRow label="Error" value={item.error_message} />
            </div>
          </div>

          <div className="mt-5 grid gap-4 lg:grid-cols-2">
            <div>
              <div className="mb-2 text-sm font-bold text-slate-900">Payload</div>
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
                {JSON.stringify(payload, null, 2)}
              </pre>
            </div>
            <div>
              <div className="mb-2 text-sm font-bold text-slate-900">Result</div>
              <pre className="max-h-80 overflow-auto rounded-lg bg-slate-950 p-4 text-xs text-slate-100">
                {item.result_json || "No result recorded."}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function RouterActionsPage() {
  const [items, setItems] = useState<RouterAction[]>([]);
  const [summary, setSummary] = useState<RouterActionsSummaryResponse["summary"] | null>(null);
  const [selected, setSelected] = useState<RouterAction | null>(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [error, setError] = useState("");

  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");
  const [actionType, setActionType] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [createdBy, setCreatedBy] = useState("");

  async function loadData() {
    setLoading(true);
    setError("");
    setAuthError("");

    try {
      const params = new URLSearchParams();
      params.set("per_page", "100");

      if (q.trim()) params.set("q", q.trim());
      if (status) params.set("status", status);
      if (actionType) params.set("action_type", actionType);
      if (serviceType) params.set("service_type", serviceType);
      if (createdBy.trim()) params.set("created_by", createdBy.trim());

      const [actionsRes, summaryRes] = await Promise.all([
        apiGetWithAuth<RouterActionsResponse>(
          `/api/admin/router-actions?${params.toString()}`
        ),
        apiGetWithAuth<RouterActionsSummaryResponse>(
          "/api/admin/router-actions/summary"
        ),
      ]);

      setItems(actionsRes.data || []);
      setSummary(summaryRes.summary || null);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Failed to load router actions.";
      if (message.toLowerCase().includes("authentication")) {
        setAuthError("Please log in through the existing admin panel first.");
      } else {
        setError(message);
      }
      setItems([]);
      setSummary(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadData();
  }, []);

  const counts = summary?.by_status || {};
  const health = summary?.health;
  const flags = useMemo(() => {
    return items.reduce(
      (acc, item) => {
        const itemFlags = actionFlags(item);
        if (itemFlags.expiredReconnectQueued) acc.expiredReconnectQueued += 1;
        if (itemFlags.reconnectAfterPayment) acc.reconnectAfterPayment += 1;
        if (itemFlags.failedDisconnect) acc.failedDisconnect += 1;
        if (itemFlags.staleQueued) acc.staleQueued += 1;
        if (itemFlags.malformedPayload) acc.malformedPayload += 1;
        if (itemFlags.missingSubscriptionLink) acc.missingSubscriptionLink += 1;
        return acc;
      },
      {
        expiredReconnectQueued: 0,
        reconnectAfterPayment: 0,
        failedDisconnect: 0,
        staleQueued: 0,
        malformedPayload: 0,
        missingSubscriptionLink: 0,
      }
    );
  }, [items]);

  if (authError) {
    return (
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-6">
        <div className="text-lg font-bold text-[var(--navy)]">
          Admin login required
        </div>
        <a
          href={adminLoginUrl()}
          className="mt-4 inline-flex rounded-lg bg-[var(--navy)] px-4 py-2 text-sm font-semibold text-white"
        >
          Open Flask Admin Login
        </a>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-900">
              Router Action Queue
            </h1>
            <p className="mt-1 text-sm text-slate-600">
              Observe-only audit trail for planned MikroTik lifecycle actions.
            </p>
          </div>

          <button
            type="button"
            onClick={() => void loadData()}
            className="inline-flex h-11 items-center justify-center rounded-lg bg-slate-900 px-4 text-sm font-semibold text-white shadow-sm transition hover:opacity-90"
          >
            Refresh
          </button>
        </div>
      </div>

      {error ? (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
        <StatCard label="Total" value={summary?.total || 0} />
        <StatCard label="Queued" value={health?.queued_total ?? counts.queued ?? 0} tone="blue" />
        <StatCard label="Retrying" value={health?.retrying_total ?? counts.retrying ?? 0} tone="amber" />
        <StatCard label="Failed" value={health?.failed_total ?? counts.failed ?? 0} tone="red" />
        <StatCard
          label="Payment Reconnects"
          value={flags.reconnectAfterPayment}
          tone="emerald"
        />
        <StatCard
          label="Oldest Queued"
          value={
            health?.oldest_queued_age_minutes === null ||
            health?.oldest_queued_age_minutes === undefined
              ? "—"
              : `${health.oldest_queued_age_minutes}m`
          }
          helper={`Stale after ${health?.stale_after_minutes ?? 30}m`}
          tone="amber"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Queued Reconnects"
          value={health?.queued_reconnects ?? 0}
          helper="Watch for payment/reconnect buildup"
          tone={(health?.queued_reconnects ?? 0) >= 25 ? "amber" : "slate"}
        />
        <StatCard
          label="Stale Queued"
          value={health?.stale_queued ?? flags.staleQueued}
          helper="Queued longer than threshold"
          tone={(health?.stale_queued ?? 0) > 0 ? "amber" : "slate"}
        />
        <StatCard
          label="Malformed Payloads"
          value={health?.malformed_payloads_sample ?? flags.malformedPayload}
          helper={`Sample size ${health?.payload_sample_size ?? items.length}`}
          tone={(health?.malformed_payloads_sample ?? 0) > 0 ? "red" : "slate"}
        />
        <StatCard
          label="Enqueue Failures"
          value={health?.enqueue_metrics.failures ?? 0}
          helper="Since app process start"
          tone={(health?.enqueue_metrics.failures ?? 0) > 0 ? "red" : "slate"}
        />
      </div>

      {health?.warnings?.length ? (
        <div className="rounded-lg border border-amber-200 bg-amber-50 p-5 shadow-sm">
          <div className="text-sm font-bold text-amber-950">
            Queue Health Warnings
          </div>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {health.warnings.map((warning) => (
              <div
                key={warning.code}
                className="rounded-lg border border-amber-200 bg-white p-3 text-sm text-slate-700"
              >
                <div className="font-semibold text-slate-950">
                  {warning.message}
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {warning.code}
                  {warning.count !== null && warning.count !== undefined
                    ? ` · ${warning.count}`
                    : ""}
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {health ? (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="text-sm font-bold text-slate-900">
            Operational Signals
          </div>
          <div className="mt-4 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <StatCard
              label="Duplicate Keys"
              value={health.duplicate_detection.duplicate_action_key_hits_since_start}
              helper="Deduped since app start"
              tone={
                health.duplicate_detection.duplicate_action_key_hits_since_start > 0
                  ? "amber"
                  : "slate"
              }
            />
            <StatCard
              label="Missing Links"
              value={health.missing_subscription_links}
              helper="Actions without subscription_id"
              tone={health.missing_subscription_links > 0 ? "amber" : "slate"}
            />
            <StatCard
              label="Repeated Disconnects"
              value={health.repeated_disconnects.length}
              helper="Repeated subscription/identity pairs"
              tone={health.repeated_disconnects.length > 0 ? "amber" : "slate"}
            />
            <StatCard
              label="Average Queue Age"
              value={`${health.average_queued_age_minutes}m`}
              helper="Recent queued sample"
            />
          </div>
        </div>
      ) : null}

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-6">
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search key, identity, payload..."
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none placeholder:text-slate-400 focus:border-slate-400"
          />

          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Statuses</option>
            <option value="queued">Queued</option>
            <option value="retrying">Retrying</option>
            <option value="failed">Failed</option>
            <option value="processing">Processing</option>
            <option value="succeeded">Succeeded</option>
          </select>

          <select
            value={actionType}
            onChange={(e) => setActionType(e.target.value)}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Actions</option>
            <option value="subscription.reconnect">Reconnect</option>
            <option value="subscription.disconnect">Disconnect</option>
            <option value="subscription.suspend">Suspend</option>
            <option value="subscription.provision">Provision</option>
          </select>

          <select
            value={serviceType}
            onChange={(e) => setServiceType(e.target.value)}
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none focus:border-slate-400"
          >
            <option value="">All Services</option>
            <option value="hotspot">Hotspot</option>
            <option value="pppoe">PPPoE</option>
          </select>

          <input
            value={createdBy}
            onChange={(e) => setCreatedBy(e.target.value)}
            placeholder="Source"
            className="h-11 rounded-lg border border-slate-200 px-3 text-sm outline-none placeholder:text-slate-400 focus:border-slate-400"
          />

          <button
            type="button"
            onClick={() => void loadData()}
            className="h-11 rounded-lg bg-amber-500 px-4 text-sm font-semibold text-slate-950 shadow-sm transition hover:opacity-90"
          >
            Apply Filters
          </button>
        </div>

        <div className="mt-3 text-sm text-slate-500">
          Showing {items.length} recent action{items.length === 1 ? "" : "s"}.
        </div>
      </div>

      <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-sm">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-sm">
            <thead className="bg-slate-50">
              <tr className="text-left text-slate-600">
                <th className="px-4 py-3 font-semibold">Action</th>
                <th className="px-4 py-3 font-semibold">Status</th>
                <th className="px-4 py-3 font-semibold">Service</th>
                <th className="px-4 py-3 font-semibold">Identity</th>
                <th className="px-4 py-3 font-semibold">Source</th>
                <th className="px-4 py-3 font-semibold">Signals</th>
                <th className="px-4 py-3 font-semibold">Created</th>
                <th className="px-4 py-3 font-semibold">Age</th>
                <th className="px-4 py-3 font-semibold">Detail</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-slate-500">
                    Loading router actions...
                  </td>
                </tr>
              ) : items.length === 0 ? (
                <tr>
                  <td colSpan={9} className="px-4 py-10 text-center text-slate-500">
                    No router actions found.
                  </td>
                </tr>
              ) : (
                items.map((item) => {
                  const itemFlags = actionFlags(item);
                  return (
                    <tr key={item.id} className="align-top">
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">
                          {actionLabel(item.action_type)}
                        </div>
                        <div className="mt-1 max-w-xs truncate text-xs text-slate-500">
                          {item.correlation_id || item.action_key}
                        </div>
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
                        {item.service_type || "—"}
                        <div className="text-xs text-slate-500">
                          {item.profile_name || "No profile"}
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900">
                          {item.identity || "—"}
                        </div>
                        {item.customer_id ? (
                          <Link
                            to={`/admin-ui/customers/${item.customer_id}`}
                            className="text-xs font-semibold text-[var(--navy)] hover:underline"
                          >
                            Customer #{item.customer_id}
                          </Link>
                        ) : null}
                      </td>

                      <td className="px-4 py-4 text-slate-700">
                        {item.created_by || "—"}
                        <div className="text-xs text-slate-500">
                          Priority {item.priority}
                        </div>
                      </td>

                      <td className="px-4 py-4">
                        <div className="flex flex-wrap gap-2">
                          {itemFlags.expiredReconnectQueued ? (
                            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
                              Expired reconnect queued
                            </span>
                          ) : null}
                          {itemFlags.reconnectAfterPayment ? (
                            <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-semibold text-emerald-700 ring-1 ring-emerald-200">
                              Payment reconnect
                            </span>
                          ) : null}
                          {itemFlags.failedDisconnect ? (
                            <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 ring-1 ring-red-200">
                              Disconnect issue
                            </span>
                          ) : null}
                          {itemFlags.staleQueued ? (
                            <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-semibold text-amber-700 ring-1 ring-amber-200">
                              Stale queued
                            </span>
                          ) : null}
                          {itemFlags.malformedPayload ? (
                            <span className="rounded-full bg-red-50 px-2.5 py-1 text-xs font-semibold text-red-700 ring-1 ring-red-200">
                              Malformed payload
                            </span>
                          ) : null}
                          {itemFlags.missingSubscriptionLink ? (
                            <span className="rounded-full bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-700 ring-1 ring-slate-200">
                              Missing subscription
                            </span>
                          ) : null}
                          {!itemFlags.expiredReconnectQueued &&
                          !itemFlags.reconnectAfterPayment &&
                          !itemFlags.failedDisconnect &&
                          !itemFlags.staleQueued &&
                          !itemFlags.malformedPayload &&
                          !itemFlags.missingSubscriptionLink ? (
                            <span className="text-slate-400">—</span>
                          ) : null}
                        </div>
                      </td>

                      <td className="px-4 py-4 text-slate-700">
                        {formatDateTime(item.created_at)}
                      </td>

                      <td className="px-4 py-4 text-slate-700">
                        {item.age_minutes === null ? "—" : `${item.age_minutes}m`}
                      </td>

                      <td className="px-4 py-4">
                        <button
                          type="button"
                          onClick={() => setSelected(item)}
                          className="inline-flex h-9 items-center justify-center rounded-lg border border-slate-200 bg-white px-3 text-xs font-semibold text-slate-700 shadow-sm transition hover:border-slate-300 hover:bg-slate-50"
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {summary?.by_action_type ? (
        <div className="grid gap-4 md:grid-cols-3">
          <StatCard
            label="Reconnect"
            value={summary.by_action_type["subscription.reconnect"] || 0}
          />
          <StatCard
            label="Disconnect"
            value={summary.by_action_type["subscription.disconnect"] || 0}
          />
          <StatCard
            label="Suspend"
            value={summary.by_action_type["subscription.suspend"] || 0}
          />
        </div>
      ) : null}

      {selected ? (
        <DetailModal item={selected} onClose={() => setSelected(null)} />
      ) : null}
    </div>
  );
}
