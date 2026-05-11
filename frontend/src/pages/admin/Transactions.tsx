import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { apiGetWithAuth } from "../../lib/api";
import { adminLoginUrl } from "../../lib/adminAuth";
import {
  SortHeader,
  SummaryCard,
  QuickFilterButton,
  adminGoldButtonClass,
  adminInputClass,
  adminPrimaryButtonClass,
  adminSecondaryButtonClass,
  downloadCsvReport,
  nextSortState,
  reportFilename,
  sortRows,
  type CsvColumn,
  type SummaryMetric,
  type SortState,
} from "../../components/admin/TableTools";

type TransactionItem = {
  id: number;
  customer_id: number | null;
  customer_name: string | null;
  customer_phone?: string | null;
  account_number?: string | null;
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

type TransactionSortKey =
  | "reference"
  | "customer"
  | "package"
  | "amount"
  | "status"
  | "type"
  | "description"
  | "created";

type PaymentWindow = "" | "today" | "month";

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

function primaryReference(item: TransactionItem) {
  return (
    item.mpesa_receipt ||
    item.checkout_request_id ||
    item.merchant_request_id ||
    `TX-${item.id}`
  );
}

function isPaidTransaction(item: TransactionItem) {
  return ["success", "completed"].includes((item.status || "").toLowerCase());
}

function money(value: number) {
  return `KES ${value.toLocaleString()}`;
}

function paymentWindowRange(window: PaymentWindow) {
  if (!window) return {};

  const from = new Date();
  const to = new Date();

  if (window === "today") {
    from.setHours(0, 0, 0, 0);
    to.setHours(23, 59, 59, 999);
  } else {
    from.setDate(1);
    from.setHours(0, 0, 0, 0);
    to.setMonth(to.getMonth() + 1, 0);
    to.setHours(23, 59, 59, 999);
  }

  return {
    createdFrom: from.toISOString(),
    createdTo: to.toISOString(),
  };
}

function transactionSummary(rows: TransactionItem[]) {
  const paidRows = rows.filter((item) =>
    ["success", "completed"].includes((item.status || "").toLowerCase())
  );

  return {
    total: rows.length,
    paid: paidRows.length,
    pending: rows.filter((item) => (item.status || "").toLowerCase() === "pending").length,
    failed: rows.filter((item) =>
      ["failed", "cancelled", "voided"].includes((item.status || "").toLowerCase())
    ).length,
    totalPaid: paidRows.reduce((sum, item) => sum + (Number(item.amount) || 0), 0),
  };
}

function transactionSummaryMetrics(summary: ReturnType<typeof transactionSummary>): SummaryMetric[] {
  return [
    { label: "Total records", value: summary.total },
    { label: "Paid transactions", value: summary.paid },
    { label: "Pending transactions", value: summary.pending },
    { label: "Failed / cancelled / voided", value: summary.failed },
    { label: "Total amount paid", value: money(summary.totalPaid) },
  ];
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
  const [paymentWindow, setPaymentWindow] = useState<PaymentWindow>("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortState<TransactionSortKey>>({
    key: "created",
    direction: "desc",
  });
  const [exporting, setExporting] = useState(false);
  const [summaryRows, setSummaryRows] = useState<TransactionItem[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);

  const [pagination, setPagination] =
    useState<TransactionsResponse["pagination"] | null>(null);

  const sortedItems = useMemo(
    () =>
      sortRows<TransactionItem, TransactionSortKey>(items, sort, {
        reference: (item) => primaryReference(item),
        customer: (item) => item.customer_name,
        package: (item) => item.package_name,
        amount: (item) => item.amount,
        status: (item) => item.status,
        type: (item) => item.type,
        description: (item) => item.result_desc,
        created: (item) => item.created_at,
      }),
    [items, sort]
  );

  const summary = useMemo(() => transactionSummary(summaryRows), [summaryRows]);

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
        const range = paymentWindowRange(paymentWindow);
        if (range.createdFrom) params.set("created_from", range.createdFrom);
        if (range.createdTo) params.set("created_to", range.createdTo);

        const res = await apiGetWithAuth<TransactionsResponse>(
          `/api/admin/transactions?${params.toString()}`
        );

        if (!mounted) return;

        setItems(Array.isArray(res?.data) ? res.data : []);
        setPagination(res?.pagination ?? null);
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
  }, [page, status, txType, q, paymentWindow]);

  useEffect(() => {
    let mounted = true;

    async function loadSummary() {
      setSummaryLoading(true);

      try {
        const rows = await fetchFilteredTransactions();
        if (mounted) setSummaryRows(rows);
      } catch {
        if (mounted) setSummaryRows([]);
      } finally {
        if (mounted) setSummaryLoading(false);
      }
    }

    loadSummary();

    return () => {
      mounted = false;
    };
  }, [status, txType, q, paymentWindow, sort]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  function resetFilters() {
    setSearchInput("");
    setQ("");
    setStatus("");
    setTxType("");
    setPaymentWindow("");
    setPage(1);
  }

  async function fetchFilteredTransactions() {
    const allRows: TransactionItem[] = [];
    let nextPage = 1;
    let totalPages = 1;

    do {
      const params = new URLSearchParams();
      params.set("page", String(nextPage));
      params.set("per_page", "100");
      if (status) params.set("status", status);
      if (txType) params.set("type", txType);
      if (q) params.set("q", q);
      const range = paymentWindowRange(paymentWindow);
      if (range.createdFrom) params.set("created_from", range.createdFrom);
      if (range.createdTo) params.set("created_to", range.createdTo);

      const res = await apiGetWithAuth<TransactionsResponse>(
        `/api/admin/transactions?${params.toString()}`
      );

      allRows.push(...(Array.isArray(res?.data) ? res.data : []));
      totalPages = res?.pagination?.pages || 1;
      nextPage += 1;
    } while (nextPage <= totalPages);

    return sortRows<TransactionItem, TransactionSortKey>(allRows, sort, {
      reference: (item) => primaryReference(item),
      customer: (item) => item.customer_name,
      package: (item) => item.package_name,
      amount: (item) => item.amount,
      status: (item) => item.status,
      type: (item) => item.type,
      description: (item) => item.result_desc,
      created: (item) => item.created_at,
    });
  }

  async function exportCsv() {
    setExporting(true);
    setPageError("");

    try {
      const rows = await fetchFilteredTransactions();
      const columns: CsvColumn<TransactionItem>[] = [
        { header: "Customer name", value: (item) => item.customer_name },
        { header: "Phone", value: (item) => item.customer_phone },
        { header: "Package", value: (item) => item.package_name },
        { header: "Account number / username", value: (item) => item.account_number },
        { header: "Status", value: (item) => item.status },
        { header: "Amount paid", value: (item) => item.amount },
        { header: "Payment date", value: (item) => formatDate(item.created_at) },
        { header: "Connection type", value: (item) => item.type },
        { header: "Receipt / reference", value: (item) => primaryReference(item) },
        { header: "Description", value: (item) => item.result_desc },
      ];

      downloadCsvReport(
        rows,
        columns,
        transactionSummaryMetrics(transactionSummary(rows)),
        reportFilename("payments-report")
      );
    } catch (err: any) {
      setPageError(err?.message || "Failed to export payments report.");
    } finally {
      setExporting(false);
    }
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
            href={adminLoginUrl()}
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
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <SummaryCard label="Total records" value={summaryLoading ? "..." : summary.total} />
            <SummaryCard label="Paid" value={summaryLoading ? "..." : summary.paid} tone="green" />
            <SummaryCard label="Pending" value={summaryLoading ? "..." : summary.pending} tone="gold" />
            <SummaryCard label="Failed" value={summaryLoading ? "..." : summary.failed} tone="red" />
            <SummaryCard label="Total paid" value={summaryLoading ? "..." : money(summary.totalPaid)} tone="navy" />
          </div>

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
                  className={`${adminInputClass} w-full sm:w-[360px]`}
                />
                <button
                  type="submit"
                  className={adminPrimaryButtonClass}
                >
                  Search
                </button>
              </form>

              <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3">
                <div className="flex flex-wrap gap-2">
                  <QuickFilterButton
                    active={paymentWindow === "today"}
                    onClick={() => {
                      setPage(1);
                      setPaymentWindow("today");
                    }}
                  >
                    Today payments
                  </QuickFilterButton>
                  <QuickFilterButton
                    active={paymentWindow === "month"}
                    onClick={() => {
                      setPage(1);
                      setPaymentWindow("month");
                    }}
                  >
                    This month payments
                  </QuickFilterButton>
                </div>
                <select
                  value={status}
                  onChange={(e) => {
                    setPage(1);
                    setStatus(e.target.value);
                  }}
                  className={adminInputClass}
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
                  className={adminInputClass}
                >
                  <option value="">All Types</option>
                  <option value="manual">Manual</option>
                  <option value="mpesa">M-Pesa</option>
                </select>
                <button type="button" onClick={resetFilters} className={adminSecondaryButtonClass}>
                  Clear Filters
                </button>
                <button
                  type="button"
                  onClick={exportCsv}
                  disabled={exporting}
                  className={adminGoldButtonClass}
                >
                  {exporting ? "Preparing..." : "Export Report"}
                </button>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3">
                      <SortHeader label="Receipt / Ref" sortKey="reference" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Customer" sortKey="customer" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Package" sortKey="package" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Amount" sortKey="amount" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Status" sortKey="status" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Type" sortKey="type" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Description" sortKey="description" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Created" sortKey="created" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3 font-bold text-black/70">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td
                        colSpan={9}
                        className="px-4 py-8 text-center text-black/55"
                      >
                        No transactions found.
                      </td>
                    </tr>
                  ) : (
                    sortedItems.map((item) => {
                      const primaryRef = primaryReference(item);
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

                          <td className="px-4 py-4 whitespace-nowrap">
                            {isPaidTransaction(item) ? (
                              <Link
                                to={`/admin-ui/transactions/${item.id}/receipt`}
                                className="inline-flex rounded-xl bg-[var(--gold)] px-3 py-2 text-xs font-black text-black shadow-[0_4px_0_rgba(0,0,0,0.18)] transition hover:-translate-y-0.5 active:translate-y-0.5"
                              >
                                Print Receipt
                              </Link>
                            ) : (
                              <span className="text-xs font-semibold text-black/40">
                                —
                              </span>
                            )}
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
