import { useMemo, useState } from "react";
import { apiPost } from "../../lib/api";

type FormState = {
  name: string;
  phone: string;
  estate: string;
  message: string;
};

type SubmitStatus = "idle" | "sent" | "error";

export default function CoveragePreview() {
  const [status, setStatus] = useState<SubmitStatus>("idle");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string>("");

  const [form, setForm] = useState<FormState>({
    name: "",
    phone: "",
    estate: "",
    message: "",
  });

  const coverageAreas = useMemo(
    () => [
      "Roysambu",
      "Kahawa Wendani",
      "Rosters",
      "Githurai",
      "Kasarani",
      "Thika Road Corridor",
      "Kiambu Road (select areas)",
      "Zimmerman",
    ],
    []
  );

  function onChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
    if (status !== "idle") setStatus("idle");
    if (errorMsg) setErrorMsg("");
  }

  async function submit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    if (loading) return;

    setLoading(true);
    setStatus("idle");
    setErrorMsg("");

    const payload = {
      name: form.name.trim(),
      phone: form.phone.trim(),
      estate: form.estate.trim(),
      message: form.message.trim(),
      source: "website",
    };

    if (!payload.name || !payload.phone || !payload.estate) {
      setStatus("error");
      setErrorMsg("Name, phone, and estate are required.");
      setLoading(false);
      return;
    }

    try {
      const res = await apiPost<{ ok: boolean; id?: number }>(
        "/api/public/leads/coverage",
        payload
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
        <div className="flex flex-col lg:flex-row gap-8 items-start">
          {/* Left */}
          <div className="flex-1">
            <h2 className="text-3xl font-extrabold text-[var(--navy)]">
              Coverage Areas
            </h2>
            <p className="mt-3 text-black/65 max-w-xl">
              We’re expanding steadily. If your area isn’t listed, request
              coverage — we’ll confirm availability and plan an install.
            </p>

            <div className="mt-6 grid sm:grid-cols-2 gap-3">
              {coverageAreas.map((a) => (
                <div
                  key={a}
                  className="rounded-xl border border-black/5 bg-[var(--gray-light)] px-4 py-3"
                >
                  <div className="text-sm font-semibold text-black">{a}</div>
                  <div className="text-xs text-black/55 mt-1">
                    Availability may vary by estate/street
                  </div>
                </div>
              ))}
            </div>

            <div className="mt-6 rounded-2xl border border-black/5 bg-[var(--gray-light)] p-5">
              <div className="text-sm font-extrabold text-black">
                Quick check
              </div>
              <div className="text-sm text-black/65 mt-1">
                Share your estate name and we’ll confirm coverage.
              </div>
            </div>
          </div>

          {/* Right: Request Coverage Form */}
          <div className="w-full lg:w-[420px]">
            <div className="rounded-2xl overflow-hidden border border-black/5 shadow-lg">
              <div className="bg-[var(--navy)] text-white px-6 py-5">
                <div className="text-xl font-extrabold">Request Coverage</div>
                <div className="text-white/80 text-sm mt-1">
                  Fill this and we’ll get back to you fast.
                </div>
              </div>

              <form onSubmit={submit} className="bg-white px-6 py-6 space-y-4">
                <div>
                  <label className="text-sm font-semibold text-black">
                    Name
                  </label>
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
                    Notes (optional)
                  </label>
                  <textarea
                    value={form.message}
                    onChange={(e) => onChange("message", e.target.value)}
                    placeholder="House type, landmark, preferred install time..."
                    rows={3}
                    className="mt-1 w-full rounded-xl border border-black/10 px-4 py-3 outline-none focus:border-[var(--gold)] resize-none"
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[var(--gold)] text-black font-extrabold px-6 py-3 rounded-xl shadow-lg transition transform hover:-translate-y-1 hover:shadow-2xl active:translate-y-0 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {loading ? "Sending..." : "Submit Request"}
                </button>

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
      </div>
    </section>
  );
}
