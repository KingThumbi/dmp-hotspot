import { useEffect, useState } from "react";
import { apiGetWithAuth } from "../../lib/api";

type PublicLead = {
  id: number;
  kind: string | null;
  name: string | null;
  phone: string | null;
  email: string | null;
  estate: string | null;
  message: string | null;
  source: string | null;
  handled: boolean | null;
  created_at: string | null;
};

type PublicLeadsResponse = {
  ok: boolean;
  data: PublicLead[];
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

function kindBadge(kind: string | null) {
  const value = (kind || "lead").toLowerCase();

  const styles: Record<string, string> = {
    coverage: "bg-blue-100 text-blue-800",
    quote: "bg-amber-100 text-amber-800",
    support: "bg-red-100 text-red-800",
    contact: "bg-emerald-100 text-emerald-800",
    lead: "bg-gray-100 text-gray-800",
  };

  return (
    <span
      className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold ${
        styles[value] || styles.lead
      }`}
    >
      {value}
    </span>
  );
}

export default function PublicLeadsPage() {
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [leads, setLeads] = useState<PublicLead[]>([]);
  const [kind, setKind] = useState("");
  const [q, setQ] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [page, setPage] = useState(1);
  const [pagination, setPagination] = useState<PublicLeadsResponse["pagination"] | null>(null);

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
        if (kind) params.set("kind", kind);
        if (q) params.set("q", q);

        const res = await apiGetWithAuth<PublicLeadsResponse>(
          `/api/admin/public-leads?${params.toString()}`
        );

        if (!mounted) return;

        setLeads(res.data || []);
        setPagination(res.pagination);
      } catch (err: any) {
        if (!mounted) return;

        const msg = err?.message || "Failed to load public leads.";
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
  }, [page, kind, q]);

  function applySearch(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setPage(1);
    setQ(searchInput.trim());
  }

  return (
    <section className="section-pad bg-[var(--gray-light)] min-h-screen">
      <div className="container-page">
        <div className="mb-8">
          <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
            Public Leads
          </h1>
          <p className="mt-2 text-black/60">
            Read-only view of coverage, quote, and support requests from the website.
          </p>
        </div>

        {loading && (
          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            Loading leads...
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
              <div className="flex flex-col lg:flex-row gap-4 lg:items-end lg:justify-between">
                <form onSubmit={applySearch} className="flex flex-col sm:flex-row gap-3 w-full lg:w-auto">
                  <input
                    value={searchInput}
                    onChange={(e) => setSearchInput(e.target.value)}
                    placeholder="Search name, phone, estate, message..."
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
                    value={kind}
                    onChange={(e) => {
                      setPage(1);
                      setKind(e.target.value);
                    }}
                    className="rounded-xl border border-black/10 px-4 py-3 bg-white outline-none focus:border-[var(--gold)]"
                  >
                    <option value="">All</option>
                    <option value="coverage">Coverage</option>
                    <option value="quote">Quote</option>
                    <option value="support">Support</option>
                    <option value="contact">Contact</option>
                  </select>
                </div>
              </div>
            </div>

            <div className="rounded-2xl bg-white border border-black/5 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="min-w-full text-sm">
                  <thead className="bg-black/5 text-left">
                    <tr>
                      <th className="px-4 py-3 font-bold text-black/70">Type</th>
                      <th className="px-4 py-3 font-bold text-black/70">Name</th>
                      <th className="px-4 py-3 font-bold text-black/70">Phone</th>
                      <th className="px-4 py-3 font-bold text-black/70">Estate</th>
                      <th className="px-4 py-3 font-bold text-black/70">Message</th>
                      <th className="px-4 py-3 font-bold text-black/70">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {leads.length === 0 ? (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-black/55">
                          No public leads found.
                        </td>
                      </tr>
                    ) : (
                      leads.map((lead) => (
                        <tr key={lead.id} className="border-t border-black/5 align-top">
                          <td className="px-4 py-4">{kindBadge(lead.kind)}</td>
                          <td className="px-4 py-4">
                            <div className="font-bold text-black">{lead.name || "—"}</div>
                            {lead.email ? (
                              <div className="text-xs text-black/50 mt-1">{lead.email}</div>
                            ) : null}
                          </td>
                          <td className="px-4 py-4 text-black/75">{lead.phone || "—"}</td>
                          <td className="px-4 py-4 text-black/75">{lead.estate || "—"}</td>
                          <td className="px-4 py-4 text-black/75 max-w-[320px]">
                            <div className="whitespace-pre-wrap break-words">
                              {lead.message || "—"}
                            </div>
                          </td>
                          <td className="px-4 py-4 text-black/55 whitespace-nowrap">
                            {formatDate(lead.created_at)}
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
      </div>
    </section>
  );
}