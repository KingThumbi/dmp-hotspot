import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGetWithAuth } from "../../lib/api";

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

type TicketItem = {
  id: number;
  code: string | null;
  subject: string | null;
  status: string | null;
  priority: string | null;
  category: string | null;
  opened_at_utc: string | null;
};

type LocationItem = {
  id: number;
  name: string | null;
  label: string | null;
  estate: string | null;
  address: string | null;
  is_primary: boolean | null;
  created_at: string | null;
};

type CustomerDetailResponse = {
  ok: boolean;
  data: {
    customer: CustomerItem;
    subscriptions: SubscriptionItem[];
    tickets: TicketItem[];
    locations: LocationItem[];
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

function TicketStatusPill({ value }: { value: string | null }) {
  const v = (value || "").toLowerCase();
  const cls =
    v === "open"
      ? "bg-blue-100 text-blue-800"
      : v === "assigned"
      ? "bg-amber-100 text-amber-800"
      : v === "in_progress"
      ? "bg-purple-100 text-purple-800"
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

function SubscriptionStatusPill({ value }: { value: string | null }) {
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

export default function CustomerDetailPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [data, setData] = useState<CustomerDetailResponse["data"] | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const res = await apiGetWithAuth<CustomerDetailResponse>(`/api/admin/customers/${id}`);
        if (!mounted) return;
        setData(res.data);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load customer detail.";
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
            Customer Detail
          </h1>
          <p className="mt-2 text-black/60">
            Read-only customer profile from the live backend.
          </p>
        </div>

        <Link
          to="/admin-ui/customers"
          className="px-4 py-2 rounded-xl border border-black/10 bg-white font-bold"
        >
          Back to Customers
        </Link>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading customer...
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
                  {data.customer.full_name || "—"}
                </div>
                <div className="mt-2 text-sm text-black/60">
                  {data.customer.customer_number || data.customer.account_number || "—"}
                </div>
              </div>
              <StatusPill active={data.customer.is_active} />
            </div>

            <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div>
                <div className="text-black/50 font-semibold">Phone</div>
                <div className="mt-1 text-black">{data.customer.phone || "—"}</div>
              </div>
              <div>
                <div className="text-black/50 font-semibold">Email</div>
                <div className="mt-1 text-black">{data.customer.email || "—"}</div>
              </div>
              <div>
                <div className="text-black/50 font-semibold">City</div>
                <div className="mt-1 text-black">{data.customer.city || "—"}</div>
              </div>
              <div>
                <div className="text-black/50 font-semibold">Address</div>
                <div className="mt-1 text-black">{data.customer.address || "—"}</div>
              </div>
              <div>
                <div className="text-black/50 font-semibold">Created</div>
                <div className="mt-1 text-black">{formatDate(data.customer.created_at)}</div>
              </div>
              <div>
                <div className="text-black/50 font-semibold">Updated</div>
                <div className="mt-1 text-black">{formatDate(data.customer.updated_at)}</div>
              </div>
            </div>
          </div>

          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <h2 className="text-xl font-black text-[var(--navy)]">Subscriptions</h2>

            {data.subscriptions.length === 0 ? (
              <div className="mt-4 text-black/55">No subscriptions found.</div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-black/5 text-left">
                    <tr>
                      <th className="px-4 py-3 font-bold text-black/70">Package</th>
                      <th className="px-4 py-3 font-bold text-black/70">Service</th>
                      <th className="px-4 py-3 font-bold text-black/70">Status</th>
                      <th className="px-4 py-3 font-bold text-black/70">Location</th>
                      <th className="px-4 py-3 font-bold text-black/70">Expiry / Due</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.subscriptions.map((item) => (
                      <tr key={item.id} className="border-t border-black/5">
                        <td className="px-4 py-3">{item.package_name || "—"}</td>
                        <td className="px-4 py-3">{item.service_type || "—"}</td>
                        <td className="px-4 py-3">
                          <SubscriptionStatusPill value={item.status} />
                        </td>
                        <td className="px-4 py-3">{item.location_name || "—"}</td>
                        <td className="px-4 py-3">
                          {formatDate(item.expires_at || item.next_due_date || item.ends_at)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <h2 className="text-xl font-black text-[var(--navy)]">Tickets</h2>

            {data.tickets.length === 0 ? (
              <div className="mt-4 text-black/55">No tickets found.</div>
            ) : (
              <div className="mt-4 overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-black/5 text-left">
                    <tr>
                      <th className="px-4 py-3 font-bold text-black/70">Code</th>
                      <th className="px-4 py-3 font-bold text-black/70">Subject</th>
                      <th className="px-4 py-3 font-bold text-black/70">Category</th>
                      <th className="px-4 py-3 font-bold text-black/70">Priority</th>
                      <th className="px-4 py-3 font-bold text-black/70">Status</th>
                      <th className="px-4 py-3 font-bold text-black/70">Opened</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tickets.map((ticket) => (
                      <tr key={ticket.id} className="border-t border-black/5">
                        <td className="px-4 py-3 font-bold text-[var(--navy)]">{ticket.code || "—"}</td>
                        <td className="px-4 py-3">{ticket.subject || "—"}</td>
                        <td className="px-4 py-3">{ticket.category || "—"}</td>
                        <td className="px-4 py-3">{ticket.priority || "—"}</td>
                        <td className="px-4 py-3">
                          <TicketStatusPill value={ticket.status} />
                        </td>
                        <td className="px-4 py-3">{formatDate(ticket.opened_at_utc)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <h2 className="text-xl font-black text-[var(--navy)]">Locations</h2>

            {data.locations.length === 0 ? (
              <div className="mt-4 text-black/55">No locations found.</div>
            ) : (
              <div className="mt-4 grid md:grid-cols-2 gap-4">
                {data.locations.map((location) => (
                  <div key={location.id} className="rounded-xl border border-black/10 p-4">
                    <div className="font-bold text-black">
                      {location.name || location.label || location.estate || "Location"}
                    </div>
                    <div className="mt-2 text-sm text-black/65">
                      {location.address || location.estate || "—"}
                    </div>
                    <div className="mt-2 text-xs text-black/50">
                      {location.is_primary ? "Primary location" : "Additional location"}
                    </div>
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