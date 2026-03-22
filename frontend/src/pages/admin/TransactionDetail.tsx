import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
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

type TransactionDetailResponse = {
  ok: boolean;
  data: {
    transaction: TransactionItem;
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

function DetailItem({
  label,
  value,
  preserveWhitespace = false,
}: {
  label: string;
  value: string;
  preserveWhitespace?: boolean;
}) {
  return (
    <div>
      <div className="text-black/50 font-semibold">{label}</div>
      <div
        className={`mt-1 text-black break-words ${
          preserveWhitespace ? "whitespace-pre-wrap" : ""
        }`}
      >
        {value || "—"}
      </div>
    </div>
  );
}

export default function TransactionDetailPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [item, setItem] = useState<TransactionItem | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const res = await apiGetWithAuth<TransactionDetailResponse>(
          `/api/admin/transactions/${id}`
        );

        if (!mounted) return;
        setItem(res.data.transaction);
      } catch (err: any) {
        if (!mounted) return;

        const msg = err?.message || "Failed to load transaction detail.";
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

  const displayRef =
    item?.mpesa_receipt ||
    item?.checkout_request_id ||
    item?.merchant_request_id ||
    (item ? `Transaction #${item.id}` : "Transaction");

  return (
    <>
      <div className="mb-8 flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl md:text-4xl font-extrabold text-[var(--navy)]">
            Transaction Detail
          </h1>
          <p className="mt-2 text-black/60">
            Read-only billing transaction detail from the live backend.
          </p>
        </div>

        <Link
          to="/admin-ui/transactions"
          className="px-4 py-2 rounded-xl border border-black/10 bg-white font-bold"
        >
          Back to Transactions
        </Link>
      </div>

      {loading && (
        <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
          Loading transaction...
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

      {!loading && !authError && !pageError && item && (
        <div className="space-y-6">
          <div className="rounded-2xl bg-white border border-black/5 p-6 shadow-sm">
            <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
              <div>
                <div className="text-2xl font-black text-black">{displayRef}</div>
                <div className="mt-2 text-sm text-black/60">
                  Customer:{" "}
                  {item.customer_name || `Customer #${item.customer_id ?? "—"}`}
                </div>
              </div>

              <div className="flex flex-wrap gap-2">
                <StatusPill value={item.status} />
                <TypePill value={item.type || item.result_code} />
              </div>
            </div>

            <div className="mt-6 grid sm:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <DetailItem
                label="Customer"
                value={item.customer_name || `Customer #${item.customer_id ?? "—"}`}
              />
              <DetailItem
                label="Package"
                value={item.package_name || `Package #${item.package_id ?? "—"}`}
              />
              <DetailItem
                label="Amount"
                value={item.amount != null ? `KES ${item.amount}` : "—"}
              />
              <DetailItem label="Receipt" value={item.mpesa_receipt || "—"} />
              <DetailItem
                label="Checkout Request ID"
                value={item.checkout_request_id || "—"}
              />
              <DetailItem
                label="Merchant Request ID"
                value={item.merchant_request_id || "—"}
              />
              <DetailItem label="Result Code" value={item.result_code || "—"} />
              <DetailItem
                label="Created At"
                value={formatDate(item.created_at)}
              />
            </div>

            <div className="mt-6">
              <div className="text-black/50 font-semibold">Description</div>
              <div className="mt-2 text-black break-words whitespace-pre-wrap">
                {item.result_desc || "—"}
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
}