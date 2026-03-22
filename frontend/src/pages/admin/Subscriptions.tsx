import { useEffect, useState } from "react";
import { apiGetWithAuth } from "../../lib/api";

type SubscriptionItem = {
  id: number;
  customer_id: number | null;
  customer_name: string | null;
  package_id: number | null;
  package_name: string | null;
  location_id: number | null;
  location_name: string | null;
  status: string | null;
  service_type: string | null;
  starts_at: string | null;
  ends_at: string | null;
  expires_at: string | null;
  next_due_date: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type SubscriptionsResponse = {
  ok: boolean;
  data: SubscriptionItem[];
  pagination: {
    page: number;
    per_page: number;
    total: number;
    pages: number;
    has_next: boolean;
    has_prev: boolean;
  };
};

function formatDate(value: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function StatusPill({ value }: { value: string | null }) {
  const v = (value || "").toLowerCase();
  const cls =
    v === "active"
      ? "bg-emerald-100 text-emerald-800"
      : v === "expired"
      ? "bg-red-100 text-red-800"
      : v === "inactive" || v === "suspended"
      ? "bg-amber-100 text-amber-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}>
      {value || "—"}
    </span>
  );
}

function ServiceTypePill({ value }: { value: string | null }) {
  const v = (value || "").toLowerCase();
  const cls =
    v === "pppoe"
      ? "bg-blue-100 text-blue-800"
      : v === "hotspot"
      ? "bg-purple-100 text-purple-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}>
      {value || "—"}
    </span>
  );
}

export default function SubscriptionsPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [items, setItems] = useState<SubscriptionItem[]>([]);
  const [status, setStatus] = useState("");
  const [serviceType, setServiceType] = useState("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<SubscriptionsResponse["pagination"] | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const params = new URLSearchParams();
        params.set("page", String(page));
        params.set("per_page", "20");
        if (status) params.set("status", status);
        if (serviceType) params.set("service_type", serviceType);
        if (q) params.set("q", q);

        const res = await apiGetWithAuth<SubscriptionsResponse>(
          `/api/admin/subscriptions?${params.toString()}`
        );

        if (!mounted) return;
        setItems(res.data || []);
        setPagination(res.pagination);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load subscriptions.";
        if (msg.toLowerCase().includes("authentication required")) {
          setAuthError("Please log in through the existing admin panel first.");
        } else {
          setPageError(msg);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [page, status, serviceType, q]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
          Subscriptions
        </h1>
        <p className="mt-2 text-black/60">
          Read-only subscription view from the live backend.
        </p>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading subscriptions...
        </div>
      )}

      {!loading && authError && (
        <div className="rounded-2xl bg-white border border-yellow-300 p-6 shadow-sm">
          <div className="text-lg font-bold text-[var(--navy)]">Admin login required</div>
          <p className="mt-2 text-black/70">{authError}</p>
          <a
            href={`${import.meta.env.VITE_API_BASE_URL || ""}/admin/login`}
            className="inline-block mt-4 px-5 py-3 rounded-xl bg-[var(--gold)] text-black font-extrabold"
          >
            Open Flask Admin Login
          </a>
        </div>
      )}

      {!loading && !authError && pageError && (
        <div className="rounded-2xl bg-white border border-red-200 p-6 shadow-sm text-red-700 font-semibold">
          {pageError}
        </div>
      )}

      {!loading && !authError && !pageError && (
        <>
          <div className="rounded-2xl bg-white border border-black/5 p-5 shadow-sm mb-6">
            <div className="flex flex-col xl:flex-row gap-4 xl:items-end xl:justify-between">
              <form onSubmit={applySearch} className="flex flex-col sm:flex-row gap-3 w-full xl:w-auto">
                <input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search customer or package..."
                  className="w-full sm:w-[320px] rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
                />
                <button
                  type="submit"
                  className="rounded-xl bg-[var(--navy)] text-white px-5 py-3 font-extrabold"
                >
                  Search
                </button>
              </form>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <select
                  value={status}
                  onChange={(e) => {
                    setPage(1);
                    setStatus(e.target.value);
                  }}
                  className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                >
                  <option value="">All Statuses</option>
                  <option value="active">Active</option>
                  <option value="expired">Expired</option>
                  <option value="inactive">Inactive</option>
                  <option value="suspended">Suspended</option>
                </select>

                <select
                  value={serviceType}
                  onChange={(e) => {
                    setPage(1);
                    setServiceType(e.target.value);
                  }}
                  className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                >
                  <option value="">All Service Types</option>
                  <option value="pppoe">PPPoE</option>
                  <option value="hotspot">Hotspot</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3 font-bold text-black/70">Customer</th>
                    <th className="px-4 py-3 font-bold text-black/70">Package</th>
                    <th className="px-4 py-3 font-bold text-black/70">Service Type</th>
                    <th className="px-4 py-3 font-bold text-black/70">Status</th>
                    <th className="px-4 py-3 font-bold text-black/70">Location</th>
                    <th className="px-4 py-3 font-bold text-black/70">Expiry / Due</th>
                    <th className="px-4 py-3 font-bold text-black/70">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-black/55">
                        No subscriptions found.
                      </td>
                    </tr>
                  ) : (
                    items.map((item) => (
                      <tr key={item.id} className="border-t border-black/5 align-top">
                        <td className="px-4 py-4">
                          <div className="font-bold text-black">{item.customer_name || `Customer #${item.customer_id ?? "—"}`}</div>
                        </td>
                        <td className="px-4 py-4 text-black/75">{item.package_name || "—"}</td>
                        <td className="px-4 py-4"><ServiceTypePill value={item.service_type} /></td>
                        <td className="px-4 py-4"><StatusPill value={item.status} /></td>
                        <td className="px-4 py-4 text-black/75">{item.location_name || "—"}</td>
                        <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                          {formatDate(item.expires_at || item.next_due_date || item.ends_at)}
                        </td>
                        <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                          {formatDate(item.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {pagination && (
            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="text-sm text-black/60">
                Page {pagination.page} of {pagination.pages || 1} • Total {pagination.total}
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  className="px-4 py-2 rounded-xl border border-black/10 bg-white disabled:opacity-50"
                >
                  Previous
                </button>
                <button
                  type="button"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                  className="px-4 py-2 rounded-xl border border-black/10 bg-white disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </>
  );
}