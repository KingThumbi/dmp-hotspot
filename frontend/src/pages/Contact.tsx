import { useState } from "react";
import { apiPost } from "../lib/api";
import Button3D from "../components/ui/Button3D";

type FormState = {
  name: string;
  phone: string;
  estate: string;
  message: string;
};

type SubmitStatus = "idle" | "sent" | "error";

export default function ContactPage() {
  const [status, setStatus] = useState<SubmitStatus>("idle");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const [form, setForm] = useState<FormState>({
    name: "",
    phone: "",
    estate: "",
    message: "",
  });

  function onChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (status !== "idle") setStatus("idle");
    if (errorMsg) setErrorMsg("");
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setLoading(true);
    setStatus("idle");
    setErrorMsg("");

    try {
      const res = await apiPost<{ ok: boolean; id: number }>(
        "/api/public/leads/quote",
        {
          name: form.name.trim(),
          phone: form.phone.trim(),
          estate: form.estate.trim(),
          message: form.message.trim(),
          source: "website",
        }
      );

      if (res?.ok) {
        setStatus("sent");
        setForm({ name: "", phone: "", estate: "", message: "" });
      } else {
        setStatus("error");
        setErrorMsg("Something failed. Try again.");
      }
    } catch (err: any) {
      setStatus("error");
      setErrorMsg(err?.message || "Something failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="section-pad bg-white">
      <div className="container-page">
        <div className="max-w-3xl">
          <h1 className="text-4xl font-extrabold text-[var(--navy)]">
            Contact Dmpolin Connect
          </h1>
          <p className="mt-3 text-black/65">
            Need a quote, installation, or support? Send us your details and we’ll
            get back to you fast.
          </p>
        </div>

        <div className="mt-10 grid lg:grid-cols-2 gap-8 items-start">
          {/* Left: Info card */}
          <div className="rounded-2xl border border-black/5 bg-[var(--gray-light)] p-6">
            <div className="text-sm font-extrabold text-black">
              Quick contacts
            </div>

            <div className="mt-4 space-y-3 text-sm text-black/70">
              <div>
                <div className="font-semibold text-black">WhatsApp</div>
                <div>Tap the WhatsApp button on the site to chat instantly.</div>
              </div>

              <div>
                <div className="font-semibold text-black">Coverage</div>
                <div>
                  For coverage checks, use the Coverage form on the homepage.
                </div>
              </div>

              <div className="pt-2 text-xs text-black/50">
                We’ll only use your details to respond to your request.
              </div>
            </div>
          </div>

          {/* Right: Quote form */}
          <div className="rounded-2xl overflow-hidden border border-black/5 shadow-lg">
            <div className="bg-[var(--navy)] text-white px-6 py-5">
              <div className="text-xl font-extrabold">Request a Quote</div>
              <div className="text-white/80 text-sm mt-1">
                Tell us your estate and what you need.
              </div>
            </div>

            <form onSubmit={submit} className="bg-white px-6 py-6 space-y-4">
              <div>
                <label className="text-sm font-semibold text-black">Name</label>
                <input
                  value={form.name}
                  onChange={(e) => onChange("name", e.target.value)}
                  placeholder="Your name"
                  className="mt-1 w-full rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
                  required
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-black">
                  Phone (Mobile/Landline)
                </label>
                <input
                  value={form.phone}
                  onChange={(e) => onChange("phone", e.target.value)}
                  placeholder="07xx xxx xxx"
                  className="mt-1 w-full rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
                  required
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-black">
                  Estate / Area
                </label>
                <input
                  value={form.estate}
                  onChange={(e) => onChange("estate", e.target.value)}
                  placeholder="e.g. Membley, Kimbo, Kahawa Sukari..."
                  className="mt-1 w-full rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)]"
                  required
                />
              </div>

              <div>
                <label className="text-sm font-semibold text-black">
                  Message
                </label>
                <textarea
                  value={form.message}
                  onChange={(e) => onChange("message", e.target.value)}
                  placeholder="What package are you interested in? Any questions?"
                  rows={4}
                  className="mt-1 w-full rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)] resize-none"
                  required
                />
              </div>

              <Button3D
                type="submit"
                disabled={loading}
                className="w-full font-extrabold"
              >
                {loading ? "Sending..." : "Send Request"}
              </Button3D>

              {status === "sent" && (
                <div className="text-sm font-semibold text-green-700">
                  Sent! We’ll reach out shortly.
                </div>
              )}
              {status === "error" && (
                <div className="text-sm font-semibold text-red-700">
                  {errorMsg || "Something failed. Try again."}
                </div>
              )}

              <div className="text-xs text-black/50">
                We’ll only use your details to respond to this request.
              </div>
            </form>
          </div>
        </div>
      </div>
    </section>
  );
}
