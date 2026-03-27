import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { apiGetWithAuth, apiPostWithAuth } from "../../lib/api";

type Customer = {
  id: number | string;
  full_name?: string | null;
  first_name?: string | null;
  last_name?: string | null;
  email?: string | null;
  phone?: string | null;
  account_number?: string | null;
  customer_number?: string | null;
  city?: string | null;
  address?: string | null;
  is_active?: boolean | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type Subscription = {
  id: number | string;
  customer_id?: number | string | null;
  customer_name?: string | null;
  package_id?: number | string | null;
  package_name?: string | null;
  location_id?: number | string | null;
  location_name?: string | null;
  status?: string | null;
  service_type?: string | null;
  is_active?: boolean | null;
  starts_at?: string | null;
  ends_at?: string | null;
  started_at?: string | null;
  expires_at?: string | null;
  next_due_date?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
};

type Ticket = {
  id: number | string;
  code?: string | null;
  subject?: string | null;
  status?: string | null;
  priority?: string | null;
  category?: string | null;
  opened_at_utc?: string | null;
};

type LocationItem = {
  id: number | string;
  name?: string | null;
  label?: string | null;
  estate?: string | null;
  address?: string | null;
  is_primary?: boolean | null;
  created_at?: string | null;
};

type CustomerDetailData = {
  customer: Customer;
  subscriptions: Subscription[];
  tickets: Ticket[];
  locations: LocationItem[];
};

type CustomerDetailResponse = {
  ok: boolean;
  data: CustomerDetailData;
};

type CustomerActionResponse = {
  ok: boolean;
  message?: string;
  data: CustomerDetailData;
};

function formatDate(value?: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function getCustomerName(customer: Customer | null) {
  if (!customer) return "Customer";
  return (
    customer.full_name ||
    [customer.first_name, customer.last_name].filter(Boolean).join(" ") ||
    customer.account_number ||
    customer.customer_number ||
    "Customer"
  );
}

function firstDefinedDate(subscription: Subscription) {
  return (
    subscription.started_at ||
    subscription.starts_at ||
    subscription.created_at ||
    null
  );
}

function lastDefinedExpiry(subscription: Subscription) {
  return (
    subscription.expires_at ||
    subscription.ends_at ||
    subscription.next_due_date ||
    null
  );
}

export default function CustomerDetail() {
  const { customerId } = useParams<{ customerId: string }>();

  const [customer, setCustomer] = useState<Customer | null>(null);
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [tickets, setTickets] = useState<Ticket[]>([]);
  const [locations, setLocations] = useState<LocationItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<"suspend" | "reconnect" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  function applyPayload(payload: CustomerDetailData) {
    setCustomer(payload.customer || null);
    setSubscriptions(payload.subscriptions || []);
    setTickets(payload.tickets || []);
    setLocations(payload.locations || []);
  }

  async function loadCustomerDetail() {
    if (!customerId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await apiGetWithAuth<CustomerDetailResponse>(`/api/admin/customers/${customerId}`);
      applyPayload(res.data);
    } catch (err: any) {
      setError(err.message || "Failed to load customer.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCustomerDetail();
  }, [customerId]);

  async function handleSuspend() {
    if (!customer) return;

    const confirmed = window.confirm(
      `Suspend ${getCustomerName(customer)}?\n\nThis will mark the customer and subscriptions as inactive.`
    );
    if (!confirmed) return;

    setActionLoading("suspend");
    setError(null);
    setMessage(null);

    try {
      const res = await apiPostWithAuth<CustomerActionResponse>(
        `/api/admin/customers/${customer.id}/suspend`,
        { reason: "Suspended by admin from Customer Detail page" }
      );

      applyPayload(res.data);
      setMessage(res.message || "Customer suspended successfully.");
    } catch (err: any) {
      setError(err.message || "Failed to suspend customer.");
    } finally {
      setActionLoading(null);
    }
  }

  async function handleReconnect() {
    if (!customer) return;

    const confirmed = window.confirm(
      `Reconnect ${getCustomerName(customer)}?\n\nThis will restore the customer and subscriptions to active state.`
    );
    if (!confirmed) return;

    setActionLoading("reconnect");
    setError(null);
    setMessage(null);

    try {
      const res = await apiPostWithAuth<CustomerActionResponse>(
        `/api/admin/customers/${customer.id}/reconnect`,
        { reason: "Reconnected by admin from Customer Detail page" }
      );

      applyPayload(res.data);
      setMessage(res.message || "Customer reconnected successfully.");
    } catch (err: any) {
      setError(err.message || "Failed to reconnect customer.");
    } finally {
      setActionLoading(null);
    }
  }

  if (loading) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border bg-white p-6 shadow-sm">
          <p className="text-sm text-slate-600">Loading customer details...</p>
        </div>
      </div>
    );
  }

  if (error && !customer) {
    return (
      <div className="p-6">
        <div className="rounded-2xl border border-red-200 bg-red-50 p-6 shadow-sm">
          <p className="text-sm font-medium text-red-700">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6 p-6">
      <div className="rounded-2xl border bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
          <div className="space-y-3">
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                {getCustomerName(customer)}
              </h1>
              <p className="mt-1 text-sm text-slate-500">
                Customer account details and service controls.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-2">
              <span
                className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${
                  customer?.is_active
                    ? "bg-green-100 text-green-700"
                    : "bg-red-100 text-red-700"
                }`}
              >
                {customer?.is_active ? "Active" : "Suspended"}
              </span>

              {customer?.account_number ? (
                <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  Account: {customer.account_number}
                </span>
              ) : null}

              {customer?.customer_number ? (
                <span className="inline-flex rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">
                  Customer No: {customer.customer_number}
                </span>
              ) : null}
            </div>
          </div>

          <div className="flex flex-wrap gap-3">
            {customer?.is_active ? (
              <button
                type="button"
                onClick={handleSuspend}
                disabled={actionLoading !== null}
                className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionLoading === "suspend" ? "Suspending..." : "Suspend Customer"}
              </button>
            ) : (
              <button
                type="button"
                onClick={handleReconnect}
                disabled={actionLoading !== null}
                className="rounded-xl bg-green-600 px-4 py-2 text-sm font-semibold text-white shadow-sm transition hover:bg-green-700 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {actionLoading === "reconnect" ? "Reconnecting..." : "Reconnect Customer"}
              </button>
            )}
          </div>
        </div>

        {message ? (
          <div className="mt-4 rounded-xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
            {message}
          </div>
        ) : null}

        {error ? (
          <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="mt-6 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <div className="rounded-xl border bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Full Name
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">
              {getCustomerName(customer)}
            </p>
          </div>

          <div className="rounded-xl border bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Phone
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">
              {customer?.phone || "—"}
            </p>
          </div>

          <div className="rounded-xl border bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Email
            </p>
            <p className="mt-2 break-all text-sm font-medium text-slate-900">
              {customer?.email || "—"}
            </p>
          </div>

          <div className="rounded-xl border bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">
              Updated
            </p>
            <p className="mt-2 text-sm font-medium text-slate-900">
              {formatDate(customer?.updated_at)}
            </p>
          </div>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-3">
        <div className="rounded-2xl border bg-white p-6 shadow-sm xl:col-span-2">
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900">Subscriptions</h2>
            <p className="mt-1 text-sm text-slate-500">
              Operational subscription state for this customer.
            </p>
          </div>

          {subscriptions.length === 0 ? (
            <div className="rounded-xl border border-dashed p-6 text-sm text-slate-500">
              No subscriptions found for this customer.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="min-w-full border-separate border-spacing-0">
                <thead>
                  <tr>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Package
                    </th>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Service Type
                    </th>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Status
                    </th>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Active
                    </th>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Started
                    </th>
                    <th className="border-b px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-slate-500">
                      Expires
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {subscriptions.map((sub) => (
                    <tr key={sub.id} className="odd:bg-slate-50/60">
                      <td className="border-b px-4 py-3 text-sm text-slate-800">
                        {sub.package_name || "—"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-slate-800">
                        {sub.service_type || "—"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-slate-800">
                        {sub.status || "—"}
                      </td>
                      <td className="border-b px-4 py-3 text-sm">
                        <span
                          className={`inline-flex rounded-full px-2.5 py-1 text-xs font-semibold ${
                            sub.is_active
                              ? "bg-green-100 text-green-700"
                              : "bg-red-100 text-red-700"
                          }`}
                        >
                          {sub.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-slate-800">
                        {formatDate(firstDefinedDate(sub))}
                      </td>
                      <td className="border-b px-4 py-3 text-sm text-slate-800">
                        {formatDate(lastDefinedExpiry(sub))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="space-y-6">
          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold text-slate-900">Locations</h2>
              <p className="mt-1 text-sm text-slate-500">
                Linked service locations for this customer.
              </p>
            </div>

            {locations.length === 0 ? (
              <div className="rounded-xl border border-dashed p-4 text-sm text-slate-500">
                No locations found.
              </div>
            ) : (
              <div className="space-y-3">
                {locations.map((location) => (
                  <div key={location.id} className="rounded-xl border bg-slate-50 p-4">
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-semibold text-slate-900">
                        {location.name || location.label || location.estate || "Location"}
                      </p>
                      {location.is_primary ? (
                        <span className="inline-flex rounded-full bg-blue-100 px-2.5 py-1 text-xs font-semibold text-blue-700">
                          Primary
                        </span>
                      ) : null}
                    </div>
                    <p className="mt-2 text-sm text-slate-600">
                      {location.address || location.estate || "—"}
                    </p>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div className="rounded-2xl border bg-white p-6 shadow-sm">
            <div className="mb-4">
              <h2 className="text-lg font-bold text-slate-900">Recent Tickets</h2>
              <p className="mt-1 text-sm text-slate-500">
                Support activity linked to this customer.
              </p>
            </div>

            {tickets.length === 0 ? (
              <div className="rounded-xl border border-dashed p-4 text-sm text-slate-500">
                No tickets found.
              </div>
            ) : (
              <div className="space-y-3">
                {tickets.map((ticket) => (
                  <div key={ticket.id} className="rounded-xl border bg-slate-50 p-4">
                    <div className="flex flex-wrap items-center gap-2">
                      {ticket.code ? (
                        <span className="text-xs font-semibold uppercase tracking-wide text-slate-500">
                          {ticket.code}
                        </span>
                      ) : null}
                      {ticket.priority ? (
                        <span className="inline-flex rounded-full bg-amber-100 px-2.5 py-1 text-xs font-semibold text-amber-700">
                          {ticket.priority}
                        </span>
                      ) : null}
                    </div>

                    <p className="mt-2 text-sm font-semibold text-slate-900">
                      {ticket.subject || "Untitled ticket"}
                    </p>

                    <div className="mt-2 flex flex-wrap gap-2 text-xs text-slate-500">
                      <span>{ticket.status || "—"}</span>
                      <span>•</span>
                      <span>{ticket.category || "—"}</span>
                      <span>•</span>
                      <span>{formatDate(ticket.opened_at_utc)}</span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}