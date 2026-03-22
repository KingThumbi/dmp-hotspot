import { useEffect, useState } from "react";
import { apiGetWithAuth } from "../../lib/api";
import { Link } from "react-router-dom";

type TicketItem = {
  id: number;
  code: string | null;
  customer_id: number | null;
  customer_name: string | null;
  category: string | null;
  priority: string | null;
  status: string | null;
  subject: string | null;
  description: string | null;
  assigned_to_admin_id: number | null;
  assigned_to_name: string | null;
  opened_at_utc: string | null;
  created_at: string | null;
};

type TicketsResponse = {
  ok: boolean;
  data: TicketItem[];
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

function badgeClass(value: string | null, kind: "status" | "priority") {
  const v = (value || "").toLowerCase();

  if (kind === "status") {
    if (v === "open") return "bg-blue-100 text-blue-800";
    if (v === "assigned") return "bg-amber-100 text-amber-800";
    if (v === "in_progress") return "bg-purple-100 text-purple-800";
    if (v === "waiting_customer") return "bg-orange-100 text-orange-800";
    if (v === "resolved") return "bg-emerald-100 text-emerald-800";
    if (v === "closed") return "bg-gray-200 text-gray-800";
    return "bg-gray-100 text-gray-800";
  }

  if (v === "urgent" || v === "high") return "bg-red-100 text-red-800";
  if (v === "med" || v === "medium") return "bg-amber-100 text-amber-800";
  if (v === "low") return "bg-emerald-100 text-emerald-800";
  return "bg-gray-100 text-gray-800";
}

function Pill({
  value,
  kind,
}: {
  value: string | null;
  kind: "status" | "priority";
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${badgeClass(
        value,
        kind
      )}`}
    >
      {value || "—"}
    </span>
  );
}

export default function TicketsPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [tickets, setTickets] = useState<TicketItem[]>([]);
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<TicketsResponse["pagination"] | null>(null);

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
        if (priority) params.set("priority", priority);
        if (q) params.set("q", q);

        const res = await apiGetWithAuth<TicketsResponse>(
          `/api/admin/tickets?${params.toString()}`
        );

        if (!mounted) return;
        setTickets(res.data || []);
        setPagination(res.pagination);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load tickets.";
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
  }, [page, status, priority, q]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  return (
    <>
      <div className="mb-8">
        <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
          Tickets
        </h1>
        <p className="mt-2 text-black/60">
          Read-only support and operations ticket view from the live backend.
        </p>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading tickets...
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
                  placeholder="Search code, subject, description, customer..."
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
                  <option value="open">Open</option>
                  <option value="assigned">Assigned</option>
                  <option value="in_progress">In Progress</option>
                  <option value="waiting_customer">Waiting Customer</option>
                  <option value="resolved">Resolved</option>
                  <option value="closed">Closed</option>
                </select>

                <select
                  value={priority}
                  onChange={(e) => {
                    setPage(1);
                    setPriority(e.target.value);
                  }}
                  className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                >
                  <option value="">All Priorities</option>
                  <option value="urgent">Urgent</option>
                  <option value="high">High</option>
                  <option value="med">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="bg-black/5 text-left">
                  <tr>
                    <th className="px-4 py-3 font-bold text-black/70">Code</th>
                    <th className="px-4 py-3 font-bold text-black/70">Customer</th>
                    <th className="px-4 py-3 font-bold text-black/70">Subject</th>
                    <th className="px-4 py-3 font-bold text-black/70">Category</th>
                    <th className="px-4 py-3 font-bold text-black/70">Priority</th>
                    <th className="px-4 py-3 font-bold text-black/70">Status</th>
                    <th className="px-4 py-3 font-bold text-black/70">Assigned To</th>
                    <th className="px-4 py-3 font-bold text-black/70">Opened</th>
                  </tr>
                </thead>
                <tbody>
                  {tickets.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-8 text-center text-black/55">
                        No tickets found.
                      </td>
                    </tr>
                  ) : (
                    tickets.map((ticket) => (
                      <tr key={ticket.id} className="border-t border-black/5 align-top">
                        <td className="px-4 py-4 whitespace-nowrap">
                        <Link
                            to={`/admin-ui/tickets/${ticket.id}`}
                            className="font-bold text-[var(--navy)] hover:underline"
                        >
                            {ticket.code || "—"}
                        </Link>
                        </td>                        
                        <td className="px-4 py-4 text-black/75">
                          {ticket.customer_name || `Customer #${ticket.customer_id ?? "—"}`}
                        </td>
                        <td className="px-4 py-4 text-black/75 max-w-[320px]">
                          <div className="font-semibold text-black">{ticket.subject || "—"}</div>
                          {ticket.description ? (
                            <div className="mt-1 text-xs text-black/55 whitespace-pre-wrap break-words">
                              {ticket.description}
                            </div>
                          ) : null}
                        </td>
                        <td className="px-4 py-4 text-black/75">{ticket.category || "—"}</td>
                        <td className="px-4 py-4"><Pill value={ticket.priority} kind="priority" /></td>
                        <td className="px-4 py-4"><Pill value={ticket.status} kind="status" /></td>
                        <td className="px-4 py-4 text-black/75">
                          {ticket.assigned_to_name || "—"}
                        </td>
                        <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                          {formatDate(ticket.opened_at_utc || ticket.created_at)}
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