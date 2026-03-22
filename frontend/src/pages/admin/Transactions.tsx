import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiGetWithAuth } from "../../lib/api";

type TransactionItem = {
  id: number;
  customer_id: number | null;
  customer_name: string | null;
  package_id: number | null;
  package_name: string | null;
  amount: number | null;
  status: string | null;
  type: string | null;
  checkout_request_id: string | null;
  merchant_request_id: string | null;
  mpesa_receipt: string | null;
  result_code: string | null;
  result_desc: string | null;
  created_at: string | null;
};

type TransactionsResponse = {
  ok: boolean;
  data: TransactionItem[];
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
    v === "success" || v === "completed"
      ? "bg-emerald-100 text-emerald-800"
      : v === "pending"
      ? "bg-amber-100 text-amber-800"
      : v === "failed" || v === "cancelled" || v === "voided"
      ? "bg-red-100 text-red-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}
    >
      {value || "—"}
    </span>
  );
}

function TypePill({ value }: { value: string | null }) {
  const v = (value || "").toLowerCase();

  const cls =
    v === "manual"
      ? "bg-purple-100 text-purple-800"
      : v === "mpesa"
      ? "bg-blue-100 text-blue-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold uppercase ${cls}`}
    >
      {value || "—"}
    </span>
  );
}

export default function TransactionsPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [items, setItems] = useState<TransactionItem[]>([]);

  const [status, setStatus] = useState("");
  const [txType, setTxType] = useState("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);

  const [pagination, setPagination] =
    useState<TransactionsResponse["pagination"] | null>(null);

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
        if (txType) params.set("type", txType);
        if (q) params.set("q", q);

        const res = await apiGetWithAuth<TransactionsResponse>(
          `/api/admin/transactions?${params.toString()}`
        );

        if (!mounted) return;

        setItems(Array.isArray(res.data) ? res.data : []);
        setPagination(res.pagination ?? null);
      } catch (err: any) {
        if (!mounted) return;

        const msg = err?.message || "Failed to load transactions.";
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
  }, [page, status, txType, q]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
          Payments / Transactions
        </h1>
        <p className="mt-2 text-black/60">
          Read-only billing transaction view from the live backend.
        </p>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading transactions...
        </div>
      )}

      {!loading && authError && (
        <div className="rounded-2xl bg-white border border-yellow-300 p-6 shadow-sm">
          <div className="text-lg font-bold text-[var(--navy)]">
            Admin login required
          </div>
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
              <form
                onSubmit={applySearch}
                className="flex flex-col sm:flex-row gap-3 w-full xl:w-auto"
              >
                <input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search receipt, checkout ID, description, customer..."
                  className="w-full sm:w-[360px] rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
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
                  <option value="pending">Pending</option>
                  <option value="success">Success</option>
                  <option value="completed">Completed</option>
                  <option value="failed">Failed</option>
                  <option value="cancelled">Cancelled</option>
                  <option value="voided">Voided</option>
                </select>

                <select
                  value={txType}
                  onChange={(e) => {
                    setPage(1);
                    setTxType(e.target.value);
                  }}
                  className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                >
                  <option value="">All Types</option>
                  <option value="manual">Manual</option>
                  <option value="mpesa">M-Pesa</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Receipt / Ref
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Customer
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Package
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Amount
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Status
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Type
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Description
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">
                      Created
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td
                        colSpan={8}
                        className="px-4 py-8 text-center text-black/55"
                      >
                        No transactions found.
                      </td>
                    </tr>
                  ) : (
                    items.map((item) => {
                      const primaryRef =
                        item.mpesa_receipt ||
                        item.checkout_request_id ||
                        item.merchant_request_id ||
                        `TX-${item.id}`;

                      return (
                        <tr
                          key={item.id}
                          className="border-t border-black/5 align-top"
                        >
                          <td className="px-4 py-4">
                            <Link
                              to={`/admin-ui/transactions/${item.id}`}
                              className="font-bold text-[var(--navy)] hover:underline"
                            >
                              {primaryRef}
                            </Link>
                            {item.result_code ? (
                              <div className="text-xs text-black/50 mt-1">
                                Result code: {item.result_code}
                              </div>
                            ) : null}
                          </td>

                          <td className="px-4 py-4 text-black/75">
                            {item.customer_name ||
                              `Customer #${item.customer_id ?? "—"}`}
                          </td>

                          <td className="px-4 py-4 text-black/75">
                            {item.package_name ||
                              `Package #${item.package_id ?? "—"}`}
                          </td>

                          <td className="px-4 py-4 text-black/75 whitespace-nowrap">
                            {item.amount != null ? `KES ${item.amount}` : "—"}
                          </td>

                          <td className="px-4 py-4">
                            <StatusPill value={item.status} />
                          </td>

                          <td className="px-4 py-4">
                            <TypePill value={item.type || item.result_code} />
                          </td>

                          <td className="px-4 py-4 text-black/55 max-w-[320px]">
                            <div className="break-words whitespace-pre-wrap">
                              {item.result_desc || "—"}
                            </div>
                          </td>

                          <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                            {formatDate(item.created_at)}
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {pagination && (
            <div className="mt-6 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
              <div className="text-sm text-black/60">
                Page {pagination.page} of {pagination.pages || 1} • Total{" "}
                {pagination.total}
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