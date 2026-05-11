import { useEffect, useMemo, useState } from "react";
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

type SubscriptionItem = {
  id: number;
  customer_id: number | null;
  customer_name: string | null;
  customer_phone?: string | null;
  account_number?: string | null;
  username?: string | null;
  package_id: number | null;
  package_name: string | null;
  package_price_kes?: number | null;
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

type SubscriptionSortKey =
  | "customer"
  | "account"
  | "package"
  | "service"
  | "status"
  | "location"
  | "expiry"
  | "created";

type ExpiryWindow = "" | "two_days";

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

function getExpiryOrDueDate(item: SubscriptionItem) {
  return item.expires_at || item.next_due_date || item.ends_at || null;
}

function money(value: number) {
  return `KES ${value.toLocaleString()}`;
}

function expiryWindowRange(window: ExpiryWindow) {
  if (!window) return {};

  const from = new Date();
  const to = new Date();
  from.setHours(0, 0, 0, 0);
  to.setDate(to.getDate() + 2);
  to.setHours(23, 59, 59, 999);

  return {
    expiresFrom: from.toISOString(),
    expiresTo: to.toISOString(),
  };
}

function subscriptionSummary(rows: SubscriptionItem[]) {
  return {
    total: rows.length,
    active: rows.filter((item) => (item.status || "").toLowerCase() === "active").length,
    inactive: rows.filter((item) =>
      ["inactive", "suspended"].includes((item.status || "").toLowerCase())
    ).length,
    expired: rows.filter((item) => (item.status || "").toLowerCase() === "expired").length,
    expectedRevenue: rows.reduce(
      (sum, item) => sum + (Number(item.package_price_kes) || 0),
      0
    ),
  };
}

function subscriptionSummaryMetrics(summary: ReturnType<typeof subscriptionSummary>): SummaryMetric[] {
  return [
    { label: "Total records", value: summary.total },
    { label: "Active subscriptions", value: summary.active },
    { label: "Inactive / suspended subscriptions", value: summary.inactive },
    { label: "Expired subscriptions", value: summary.expired },
    { label: "Expected subscription revenue", value: money(summary.expectedRevenue) },
  ];
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
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}
    >
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
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}
    >
      {value || "—"}
    </span>
  );
}

function AccountNumberBadge({ value }: { value?: string | null }) {
  return (
    <span className="inline-flex rounded-lg bg-slate-100 px-3 py-1 text-xs font-bold text-slate-700">
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
  const [expiryWindow, setExpiryWindow] = useState<ExpiryWindow>("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");

  const [page, setPage] = useState(1);
  const [sort, setSort] = useState<SortState<SubscriptionSortKey>>({
    key: "expiry",
    direction: "asc",
  });
  const [exporting, setExporting] = useState(false);
  const [summaryRows, setSummaryRows] = useState<SubscriptionItem[]>([]);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [pagination, setPagination] =
    useState<SubscriptionsResponse["pagination"] | null>(null);

  const sortedItems = useMemo(
    () =>
      sortRows<SubscriptionItem, SubscriptionSortKey>(items, sort, {
        customer: (item) => item.customer_name,
        account: (item) => item.account_number,
        package: (item) => item.package_name,
        service: (item) => item.service_type,
        status: (item) => item.status,
        location: (item) => item.location_name,
        expiry: (item) => getExpiryOrDueDate(item),
        created: (item) => item.created_at,
      }),
    [items, sort]
  );

  const summary = useMemo(() => subscriptionSummary(summaryRows), [summaryRows]);

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
        const range = expiryWindowRange(expiryWindow);
        if (range.expiresFrom) params.set("expires_from", range.expiresFrom);
        if (range.expiresTo) params.set("expires_to", range.expiresTo);

        const res = await apiGetWithAuth<SubscriptionsResponse>(
          `/api/admin/subscriptions?${params.toString()}`
        );

        if (!mounted) return;

        setItems(Array.isArray(res?.data) ? res.data : []);
        setPagination(res?.pagination ?? null);
      } catch (err: any) {
        if (!mounted) return;

        const msg = err?.message || "Failed to load subscriptions.";

        if (msg.toLowerCase().includes("authentication required")) {
          setAuthError("Please log in through the existing admin panel first.");
        } else {
          setPageError(msg);
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      mounted = false;
    };
  }, [page, q, serviceType, status, expiryWindow]);

  useEffect(() => {
    let mounted = true;

    async function loadSummary() {
      setSummaryLoading(true);

      try {
        const rows = await fetchFilteredSubscriptions();
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
  }, [q, serviceType, status, expiryWindow, sort]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  function resetFilters() {
    setSearchInput("");
    setQ("");
    setStatus("");
    setServiceType("");
    setExpiryWindow("");
    setPage(1);
  }

  async function fetchFilteredSubscriptions() {
    const allRows: SubscriptionItem[] = [];
    let nextPage = 1;
    let totalPages = 1;

    do {
      const params = new URLSearchParams();
      params.set("page", String(nextPage));
      params.set("per_page", "100");
      if (status) params.set("status", status);
      if (serviceType) params.set("service_type", serviceType);
      if (q) params.set("q", q);
      const range = expiryWindowRange(expiryWindow);
      if (range.expiresFrom) params.set("expires_from", range.expiresFrom);
      if (range.expiresTo) params.set("expires_to", range.expiresTo);

      const res = await apiGetWithAuth<SubscriptionsResponse>(
        `/api/admin/subscriptions?${params.toString()}`
      );

      allRows.push(...(Array.isArray(res?.data) ? res.data : []));
      totalPages = res?.pagination?.pages || 1;
      nextPage += 1;
    } while (nextPage <= totalPages);

    return sortRows<SubscriptionItem, SubscriptionSortKey>(allRows, sort, {
      customer: (item) => item.customer_name,
      account: (item) => item.account_number,
      package: (item) => item.package_name,
      service: (item) => item.service_type,
      status: (item) => item.status,
      location: (item) => item.location_name,
      expiry: (item) => getExpiryOrDueDate(item),
      created: (item) => item.created_at,
    });
  }

  async function exportCsv() {
    setExporting(true);
    setPageError("");

    try {
      const rows = await fetchFilteredSubscriptions();
      const columns: CsvColumn<SubscriptionItem>[] = [
        { header: "Customer name", value: (item) => item.customer_name },
        { header: "Phone", value: (item) => item.customer_phone },
        { header: "Package", value: (item) => item.package_name },
        { header: "Account number / username", value: (item) => item.account_number || item.username },
        { header: "Status", value: (item) => item.status },
        { header: "Expiry date", value: (item) => formatDate(getExpiryOrDueDate(item)) },
        { header: "Expected amount", value: (item) => item.package_price_kes },
        { header: "Connection type", value: (item) => item.service_type },
        { header: "Location", value: (item) => item.location_name },
        { header: "Created date", value: (item) => formatDate(item.created_at) },
      ];

      downloadCsvReport(
        rows,
        columns,
        subscriptionSummaryMetrics(subscriptionSummary(rows)),
        reportFilename("subscriptions-report")
      );
    } catch (err: any) {
      setPageError(err?.message || "Failed to export subscriptions report.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl font-extrabold text-[var(--navy)] md:text-4xl">
          Subscriptions
        </h1>
        <p className="mt-2 text-black/60">
          Read-only subscription view from the live backend.
        </p>
      </div>

      {loading && (
        <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
          Loading subscriptions...
        </div>
      )}

      {!loading && authError && (
        <div className="rounded-2xl border border-yellow-300 bg-white p-6 shadow-sm">
          <div className="text-lg font-bold text-[var(--navy)]">
            Admin login required
          </div>
          <p className="mt-2 text-black/70">{authError}</p>
          <a
            href={adminLoginUrl()}
            className="mt-4 inline-block rounded-xl bg-[var(--gold)] px-5 py-3 font-extrabold text-black"
          >
            Open Flask Admin Login
          </a>
        </div>
      )}

      {!loading && !authError && pageError && (
        <div className="rounded-2xl border border-red-200 bg-white p-6 font-semibold text-red-700 shadow-sm">
          {pageError}
        </div>
      )}

      {!loading && !authError && !pageError && (
        <>
          <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
            <SummaryCard label="Total records" value={summaryLoading ? "..." : summary.total} />
            <SummaryCard label="Active" value={summaryLoading ? "..." : summary.active} tone="green" />
            <SummaryCard label="Inactive" value={summaryLoading ? "..." : summary.inactive} tone="gold" />
            <SummaryCard label="Expired" value={summaryLoading ? "..." : summary.expired} tone="red" />
            <SummaryCard
              label="Expected revenue"
              value={summaryLoading ? "..." : money(summary.expectedRevenue)}
              tone="navy"
            />
          </div>

          <div className="mb-6 rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
            <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
              <form
                onSubmit={applySearch}
                className="flex w-full flex-col gap-3 sm:flex-row xl:w-auto"
              >
                <input
                  value={searchInput}
                  onChange={(e) => setSearchInput(e.target.value)}
                  placeholder="Search customer, account no., or package..."
                  className={`${adminInputClass} w-full sm:w-[340px]`}
                />
                <button
                  type="submit"
                  className={adminPrimaryButtonClass}
                >
                  Search
                </button>
              </form>

              <div className="flex flex-col items-start gap-3 sm:flex-row sm:items-center">
                <div className="flex flex-wrap gap-2">
                  <QuickFilterButton
                    active={expiryWindow === "two_days"}
                    onClick={() => {
                      setPage(1);
                      setStatus("active");
                      setExpiryWindow("two_days");
                    }}
                  >
                    Expiring in 2 days
                  </QuickFilterButton>
                  <QuickFilterButton
                    active={status === "expired" && !expiryWindow}
                    onClick={() => {
                      setPage(1);
                      setStatus("expired");
                      setExpiryWindow("");
                    }}
                  >
                    Expired
                  </QuickFilterButton>
                  <QuickFilterButton
                    active={status === "active" && !expiryWindow}
                    onClick={() => {
                      setPage(1);
                      setStatus("active");
                      setExpiryWindow("");
                    }}
                  >
                    Active
                  </QuickFilterButton>
                  <QuickFilterButton
                    active={serviceType === "hotspot"}
                    onClick={() => {
                      setPage(1);
                      setServiceType("hotspot");
                    }}
                  >
                    Hotspot
                  </QuickFilterButton>
                  <QuickFilterButton
                    active={serviceType === "pppoe"}
                    onClick={() => {
                      setPage(1);
                      setServiceType("pppoe");
                    }}
                  >
                    PPPoE
                  </QuickFilterButton>
                </div>
                <select
                  value={status}
                  onChange={(e) => {
                    setPage(1);
                    setStatus(e.target.value);
                    setExpiryWindow("");
                  }}
                  className={adminInputClass}
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
                  className={adminInputClass}
                >
                  <option value="">All Service Types</option>
                  <option value="pppoe">PPPoE</option>
                  <option value="hotspot">Hotspot</option>
                </select>

                <button
                  type="button"
                  onClick={resetFilters}
                  className={adminSecondaryButtonClass}
                >
                  Clear Filters
                </button>

                <button
                  type="button"
                  onClick={exportCsv}
                  disabled={exporting}
                  className={adminGoldButtonClass}
                >
                  {exporting ? "Preparing..." : "Download CSV"}
                </button>
              </div>
            </div>
          </div>

          <div className="overflow-hidden rounded-2xl border border-black/5 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3">
                      <SortHeader label="Customer" sortKey="customer" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Account No." sortKey="account" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Package" sortKey="package" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Service Type" sortKey="service" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Status" sortKey="status" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Location" sortKey="location" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Expiry / Due" sortKey="expiry" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                    <th className="px-4 py-3">
                      <SortHeader label="Created" sortKey="created" sort={sort} onSort={(key) => setSort((current) => nextSortState(current, key))} />
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {items.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-black/55">
                        No subscriptions found.
                      </td>
                    </tr>
                  ) : (
                    sortedItems.map((item) => (
                      <tr key={item.id} className="align-top border-t border-black/5">
                        <td className="px-4 py-4">
                          <div className="font-bold text-black">
                            {item.customer_name ||
                              `Customer #${item.customer_id ?? "—"}`}
                          </div>
                        </td>

                        <td className="px-4 py-4">
                          <AccountNumberBadge value={item.account_number} />
                        </td>

                        <td className="px-4 py-4 text-black/75">
                          {item.package_name || "—"}
                        </td>

                        <td className="px-4 py-4">
                          <ServiceTypePill value={item.service_type} />
                        </td>

                        <td className="px-4 py-4">
                          <StatusPill value={item.status} />
                        </td>

                        <td className="px-4 py-4 text-black/75">
                          {item.location_name || "—"}
                        </td>

                        <td className="whitespace-nowrap px-4 py-4 text-black/55">
                          {formatDate(getExpiryOrDueDate(item))}
                        </td>

                        <td className="whitespace-nowrap px-4 py-4 text-black/55">
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
            <div className="mt-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="text-sm text-black/60">
                Page {pagination.page} of {pagination.pages || 1} • Total{" "}
                {pagination.total}
              </div>

              <div className="flex items-center gap-3">
                <button
                  type="button"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                  className="rounded-xl border border-black/10 bg-white px-4 py-2 disabled:opacity-50"
                >
                  Previous
                </button>

                <button
                  type="button"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((prev) => prev + 1)}
                  className="rounded-xl border border-black/10 bg-white px-4 py-2 disabled:opacity-50"
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
