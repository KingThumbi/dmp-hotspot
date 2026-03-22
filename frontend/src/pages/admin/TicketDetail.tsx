import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGetWithAuth } from "../../lib/api";

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

type TicketUpdateItem = {
  id: number;
  actor_admin_id: number | null;
  actor_name: string | null;
  message: string | null;
  status_from: string | null;
  status_to: string | null;
  assigned_from_admin_id: number | null;
  assigned_from_name: string | null;
  assigned_to_admin_id: number | null;
  assigned_to_name: string | null;
  created_at: string | null;
};

type TicketDetailResponse = {
  ok: boolean;
  data: {
    ticket: TicketItem;
    updates: TicketUpdateItem[];
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
    v === "open"
      ? "bg-blue-100 text-blue-800"
      : v === "assigned"
      ? "bg-amber-100 text-amber-800"
      : v === "in_progress"
      ? "bg-purple-100 text-purple-800"
      : v === "waiting_customer"
      ? "bg-orange-100 text-orange-800"
      : v === "resolved"
      ? "bg-emerald-100 text-emerald-800"
      : v === "closed"
      ? "bg-gray-200 text-gray-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}>
      {value || "—"}
    </span>
  );
}

function PriorityPill({ value }: { value: string | null }) {
  const v = (value || "").toLowerCase();
  const cls =
    v === "urgent" || v === "high"
      ? "bg-red-100 text-red-800"
      : v === "med" || v === "medium"
      ? "bg-amber-100 text-amber-800"
      : v === "low"
      ? "bg-emerald-100 text-emerald-800"
      : "bg-gray-100 text-gray-800";

  return (
    <span className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${cls}`}>
      {value || "—"}
    </span>
  );
}

export default function TicketDetailPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [data, setData] = useState<TicketDetailResponse["data"] | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const res = await apiGetWithAuth<TicketDetailResponse>(`/api/admin/tickets/${id}`);
        if (!mounted) return;
        setData(res.data);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load ticket detail.";
        if (msg.toLowerCase().includes("authentication required")) {
          setAuthError("Please log in through the existing admin panel first.");
        } else {
          setPageError(msg);
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    if (id) load();

    return () => {
      mounted = false;
    };
  }, [id]);

  return (
    <>
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
            Ticket Detail
          </h1>
          <p className="mt-2 text-black/60">
            Read-only ticket view from the live backend.
          </p>
        </div>

        <Link
          to="/admin-ui/tickets"
          className="px-4 py-2 rounded-xl border border-black/10 bg-white font-bold"
        >
          Back to Tickets
        </Link>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading ticket...
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

      {!loading && !authError && !pageError && data && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div>
                <div className="text-2xl font-black text-black">
                  {data.ticket.code || "Ticket"}
                </div>
                <div className="mt-2 text-lg font-semibold text-[var(--navy)]">
                  {data.ticket.subject || "—"}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <PriorityPill value={data.ticket.priority} />
                <StatusPill value={data.ticket.status} />
              </div>
            </div>

            <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-black/50 font-semibold">Customer</div>
                <div className="mt-1 text-black">
                  {data.ticket.customer_name || `Customer #${data.ticket.customer_id ?? "—"}`}
                </div>
              </div>

              <div>
                <div className="text-black/50 font-semibold">Category</div>
                <div className="mt-1 text-black">{data.ticket.category || "—"}</div>
              </div>

              <div>
                <div className="text-black/50 font-semibold">Assigned To</div>
                <div className="mt-1 text-black">{data.ticket.assigned_to_name || "—"}</div>
              </div>

              <div>
                <div className="text-black/50 font-semibold">Opened</div>
                <div className="mt-1 text-black">{formatDate(data.ticket.opened_at_utc)}</div>
              </div>

              <div>
                <div className="text-black/50 font-semibold">Created</div>
                <div className="mt-1 text-black">{formatDate(data.ticket.created_at)}</div>
              </div>
            </div>

            <div className="mt-6">
              <div className="text-black/50 font-semibold">Description</div>
              <div className="mt-2 text-black whitespace-pre-wrap">
                {data.ticket.description || "—"}
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <h2 className="text-xl font-black text-[var(--navy)]">Timeline / Updates</h2>

            {data.updates.length === 0 ? (
              <div className="mt-4 text-black/55">No updates found.</div>
            ) : (
              <div className="mt-6 space-y-4">
                {data.updates.map((update) => (
                  <div
                    key={update.id}
                    className="rounded-xl border border-black/10 p-4"
                  >
                    <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-3">
                      <div>
                        <div className="font-bold text-black">
                          {update.actor_name || "System / Unknown"}
                        </div>
                        <div className="text-xs text-black/50 mt-1">
                          {formatDate(update.created_at)}
                        </div>
                      </div>

                      <div className="flex flex-wrap gap-2">
                        {update.status_from || update.status_to ? (
                          <span className="text-xs rounded-full bg-black/5 px-3 py-1 font-semibold text-black/70">
                            Status: {update.status_from || "—"} → {update.status_to || "—"}
                          </span>
                        ) : null}

                        {update.assigned_from_name || update.assigned_to_name ? (
                          <span className="text-xs rounded-full bg-black/5 px-3 py-1 font-semibold text-black/70">
                            Assigned: {update.assigned_from_name || "—"} → {update.assigned_to_name || "—"}
                          </span>
                        ) : null}
                      </div>
                    </div>

                    {update.message ? (
                      <div className="mt-3 text-sm text-black whitespace-pre-wrap">
                        {update.message}
                      </div>
                    ) : null}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
}