import { useEffect, useState } from "react";
import { apiGetWithAuth } from "../../lib/api";

type AdminMeResponse = {
  ok: boolean;
  user: {
    id: number | string | null;
    name: string | null;
    email: string | null;
    role: string | null;
  };
};

type DashboardSummaryResponse = {
  ok: boolean;
  data: {
    total_customers: number;
    total_subscriptions: number;
    active_subscriptions: number;
    expired_subscriptions: number;
    open_tickets: number;
    public_leads: number;
    new_public_leads: number;
  };
};

function StatCard({
  label,
  value,
}: {
  label: string;
  value: number | string;
}) {
  return (
    <div className="rounded-2xl border border-black/5 bg-white p-5 shadow-sm">
      <div className="text-sm font-semibold text-black/55">{label}</div>
      <div className="mt-2 text-3xl font-black text-[var(--navy)]">{value}</div>
    </div>
  );
}

export default function AdminDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [user, setUser] = useState<AdminMeResponse["user"] | null>(null);
  const [summary, setSummary] = useState<DashboardSummaryResponse["data"] | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const me = await apiGetWithAuth<AdminMeResponse>("/api/admin/auth/me");
        if (!mounted) return;

        setUser(me.user);

        const dash = await apiGetWithAuth<DashboardSummaryResponse>(
          "/api/admin/dashboard/summary"
        );
        if (!mounted) return;

        setSummary(dash.data);
      } catch (err: any) {
        if (!mounted) return;

        const msg = err?.message || "Failed to load dashboard.";
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
  }, []);

  return (
    <section className="section-pad bg-[var(--gray-light)] min-h-screen">
      <div className="container-page">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
            Admin Dashboard
          </h1>
          <p className="mt-2 text-black/60">
            Read-only operational snapshot from the live backend.
          </p>
        </div>

        {loading && (
          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            Loading dashboard...
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

        {!loading && !authError && !pageError && user && summary && (
          <>
            <div className="rounded-2xl bg-white border border-black/5 p-5 shadow-sm mb-6">
              <div className="text-sm text-black/55">Signed in as</div>
              <div className="mt-1 text-xl font-bold text-black">
                {user.name || user.email || "Admin User"}
              </div>
              <div className="text-sm text-black/55 mt-1">
                Role: {user.role || "admin"}
              </div>
            </div>

            <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-5">
              <StatCard label="Total Customers" value={summary.total_customers} />
              <StatCard label="Total Subscriptions" value={summary.total_subscriptions} />
              <StatCard label="Active Subscriptions" value={summary.active_subscriptions} />
              <StatCard label="Expired Subscriptions" value={summary.expired_subscriptions} />
              <StatCard label="Open Tickets" value={summary.open_tickets} />
              <StatCard label="Public Leads" value={summary.public_leads} />
              <StatCard label="New / Unhandled Leads" value={summary.new_public_leads} />
            </div>
          </>
        )}
      </div>
    </section>
  );
}