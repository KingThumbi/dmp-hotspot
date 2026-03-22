import { useEffect, useState } from "react";
import { apiGetWithAuth } from "../../lib/api";
import { Link } from "react-router-dom";
type CustomerItem = {
  id: number;
  full_name: string | null;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  phone: string | null;
  account_number: string | null;
  customer_number: string | null;
  city: string | null;
  address: string | null;
  is_active: boolean | null;
  created_at: string | null;
  updated_at: string | null;
};

type CustomersResponse = {
  ok: boolean;
  data: CustomerItem[];
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

function StatusPill({ active }: { active: boolean | null }) {
  const text = active === null ? "—" : active ? "Active" : "Inactive";
  const cls =
    active === null
      ? "bg-gray-100 text-gray-800"
      : active
      ? "bg-emerald-100 text-emerald-800"
      : "bg-red-100 text-red-800";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}>
      {text}
    </span>
  );
}

export default function CustomersPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [active, setActive] = useState("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<CustomersResponse["pagination"] | null>(null);

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
        if (active) params.set("active", active);
        if (q) params.set("q", q);

        const res = await apiGetWithAuth<CustomersResponse>(
          `/api/admin/customers?${params.toString()}`
        );

        if (!mounted) return;
        setCustomers(res.data || []);
        setPagination(res.pagination);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load customers.";
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
  }, [page, active, q]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
          Customers
        </h1>
        <p className="mt-2 text-black/60">
          Read-only customer view from the live backend.
        </p>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading customers...
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
                  placeholder="Search name, phone, email, account number..."
                  className="w-full sm:w-[320px] rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
                />
                <button
                  type="submit"
                  className="rounded-xl bg-[var(--navy)] text-white px-5 py-3 font-extrabold"
                >
                  Search
                </button>
              </form>

              <div className="flex items-center gap-3">
                <label className="text-sm font-semibold text-black/70">Filter</label>
                <select
                  value={active}
                  onChange={(e) => {
                    setPage(1);
                    setActive(e.target.value);
                  }}
                  className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                >
                  <option value="">All</option>
                  <option value="true">Active</option>
                  <option value="false">Inactive</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3 font-bold text-black/70">Name</th>
                    <th className="px-4 py-3 font-bold text-black/70">Phone</th>
                    <th className="px-4 py-3 font-bold text-black/70">Email</th>
                    <th className="px-4 py-3 font-bold text-black/70">Account No.</th>
                    <th className="px-4 py-3 font-bold text-black/70">City</th>
                    <th className="px-4 py-3 font-bold text-black/70">Status</th>
                    <th className="px-4 py-3 font-bold text-black/70">Created</th>
                  </tr>
                </thead>
                <tbody>
                  {customers.length === 0 ? (
                    <tr>
                      <td colSpan={7} className="px-4 py-8 text-center text-black/55">
                        No customers found.
                      </td>
                    </tr>
                  ) : (
                    customers.map((customer) => (
                      <tr key={customer.id} className="border-t border-black/5 align-top">                       
                        <td className="px-4 py-4">
                        <Link
                            to={`/admin-ui/customers/${customer.id}`}
                            className="font-bold text-[var(--navy)] hover:underline"
                        >
                            {customer.full_name || "—"}
                        </Link>
                        {customer.customer_number ? (
                            <div className="text-xs text-black/50 mt-1">{customer.customer_number}</div>
                        ) : null}
                        </td>                        
                        <td className="px-4 py-4 text-black/75">{customer.phone || "—"}</td>
                        <td className="px-4 py-4 text-black/75">{customer.email || "—"}</td>
                        <td className="px-4 py-4 text-black/75">
                          {customer.account_number || "—"}
                        </td>
                        <td className="px-4 py-4 text-black/75">
                          {customer.city || customer.address || "—"}
                        </td>
                        <td className="px-4 py-4">
                          <StatusPill active={customer.is_active} />
                        </td>
                        <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                          {formatDate(customer.created_at)}
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