import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiGetWithAuth } from "../../lib/api";
import { adminLoginUrl } from "../../lib/adminAuth";
import { adminGoldButtonClass, adminSecondaryButtonClass } from "../../components/admin/TableTools";

type TransactionReceiptItem = {
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

type ReceiptSubscription = {
  id: number | null;
  status: string | null;
  service_type: string | null;
  username: string | null;
  package_name: string | null;
  starts_at: string | null;
  expires_at: string | null;
  created_at: string | null;
} | null;

type ReceiptResponse = {
  ok: boolean;
  data: {
    transaction: TransactionReceiptItem;
    subscription: ReceiptSubscription;
    generated_by: {
      id: number | null;
      name: string | null;
      email: string | null;
      role: string | null;
    };
  };
};

function formatDate(value: string | null) {
  if (!value) return "—";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return value;
  return d.toLocaleString();
}

function formatMoney(value: number | null) {
  return value == null ? "—" : `KES ${value.toLocaleString()}`;
}

function isPaid(status: string | null) {
  return ["success", "completed"].includes((status || "").toLowerCase());
}

function receiptNumber(item: TransactionReceiptItem) {
  return item.mpesa_receipt || `TX-${item.id}`;
}

function Field({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="border-b border-black/10 py-3">
      <div className="text-[11px] font-black uppercase tracking-wide text-black/45">
        {label}
      </div>
      <div className="mt-1 break-words text-sm font-bold text-black">{value || "—"}</div>
    </div>
  );
}

export default function TransactionReceiptPage() {
  const { id } = useParams();
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState("");
  const [pageError, setPageError] = useState("");
  const [receipt, setReceipt] = useState<ReceiptResponse["data"] | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      setAuthError("");
      setPageError("");

      try {
        const res = await apiGetWithAuth<ReceiptResponse>(
          `/api/admin/transactions/${id}/receipt`
        );

        if (!mounted) return;
        setReceipt(res?.data ?? null);
      } catch (err: any) {
        if (!mounted) return;
        const msg = err?.message || "Failed to load receipt.";
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

  const tx = receipt?.transaction ?? null;
  const subscription = receipt?.subscription ?? null;
  const accountOrUsername = tx?.account_number || subscription?.username || null;

  const subscriptionPeriod = useMemo(() => {
    if (!subscription?.starts_at && !subscription?.expires_at) return null;
    return `${formatDate(subscription.starts_at)} to ${formatDate(subscription.expires_at)}`;
  }, [subscription]);

  return (
    <div className="min-h-screen bg-[var(--gray-light)] py-6 print:bg-white print:py-0">
      <div className="mx-auto max-w-3xl px-4 print:max-w-none print:px-0">
        <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between print:hidden">
          <Link to="/admin-ui/transactions" className={adminSecondaryButtonClass}>
            Back to Transactions
          </Link>
          <button
            type="button"
            onClick={() => window.print()}
            disabled={!tx || !isPaid(tx.status)}
            className={adminGoldButtonClass}
          >
            Print / Save PDF
          </button>
        </div>

        {loading && (
          <div className="rounded-2xl border border-black/5 bg-white p-6 shadow-sm">
            Loading receipt...
          </div>
        )}

        {!loading && authError && (
          <div className="rounded-2xl border border-yellow-300 bg-white p-6 shadow-sm print:hidden">
            <div className="text-lg font-bold text-[var(--navy)]">Admin login required</div>
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

        {!loading && !authError && !pageError && tx && !isPaid(tx.status) && (
          <div className="rounded-2xl border border-amber-200 bg-white p-6 shadow-sm">
            <div className="text-xl font-black text-[var(--navy)]">Receipt unavailable</div>
            <p className="mt-2 text-black/70">
              This transaction is not marked as paid. Receipts are only available for successful or completed payments.
            </p>
          </div>
        )}

        {!loading && !authError && !pageError && tx && isPaid(tx.status) && (
          <article className="mx-auto max-w-[560px] overflow-hidden rounded-2xl border border-black/10 bg-white shadow-xl print:max-w-none print:rounded-none print:border-0 print:shadow-none">
            <div className="bg-[var(--navy)] px-6 py-5 text-white">
              <div className="flex items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <img
                    src="/logo.png"
                    alt="Dmpolin Connect"
                    className="h-12 w-12 rounded-xl bg-white object-contain p-1"
                  />
                  <div>
                    <div className="text-xl font-black">Dmpolin Connect</div>
                    <div className="text-xs font-semibold text-white/70">Payment Receipt</div>
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-xs font-bold uppercase text-[var(--gold)]">Receipt No.</div>
                  <div className="font-black">{receiptNumber(tx)}</div>
                </div>
              </div>
            </div>

            <div className="border-b border-[var(--gold)] bg-[var(--gold)]/15 px-6 py-4">
              <div className="text-xs font-black uppercase tracking-wide text-black/50">
                Amount paid
              </div>
              <div className="mt-1 text-4xl font-black text-[var(--navy)]">
                {formatMoney(tx.amount)}
              </div>
            </div>

            <div className="grid gap-x-6 px-6 py-4 sm:grid-cols-2">
              <Field label="Customer name" value={tx.customer_name || `Customer #${tx.customer_id ?? "—"}`} />
              <Field label="Customer phone" value={tx.customer_phone} />
              <Field label="Account / username" value={accountOrUsername} />
              <Field label="Package" value={tx.package_name || subscription?.package_name} />
              <Field label="Payment method" value="M-Pesa" />
              <Field label="M-Pesa receipt code" value={tx.mpesa_receipt} />
              <Field label="Payment date/time" value={formatDate(tx.created_at)} />
              <Field label="Subscription period" value={subscriptionPeriod || formatDate(subscription?.expires_at ?? null)} />
              <Field label="Expiry date" value={formatDate(subscription?.expires_at ?? null)} />
              <Field
                label="Served by / generated by"
                value={receipt?.generated_by?.name || receipt?.generated_by?.email || receipt?.generated_by?.role}
              />
            </div>

            <div className="px-6 pb-5 pt-2">
              <div className="rounded-xl border border-black/10 bg-slate-50 px-4 py-3 text-xs leading-relaxed text-black/60">
                This is a computer-generated receipt for a payment recorded in the Dmpolin Connect admin system.
              </div>
            </div>

            <footer className="border-t border-black/10 px-6 py-4 text-center">
              <div className="font-black text-[var(--navy)]">
                Thank you for choosing Dmpolin Connect
              </div>
            </footer>
          </article>
        )}
      </div>
    </div>
  );
}
