import { useState } from "react";
import { apiPost } from "../lib/api";
import Button3D from "../components/ui/Button3D";

type FormState = {
  name: string;
  phone: string;
  estate: string;
  message: string;
};

export default function SupportPage() {
  const [form, setForm] = useState<FormState>({
    name: "",
    phone: "",
    estate: "",
    message: "",
  });

  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState<"idle" | "sent" | "error">("idle");
  const [errorMsg, setErrorMsg] = useState("");

  function onChange<K extends keyof FormState>(key: K, value: FormState[K]) {
    setForm((prev) => ({ ...prev, [key]: value }));
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (loading) return;

    setLoading(true);
    setStatus("idle");

    try {
      const res = await apiPost<{ ok: boolean; id: number }>(
        "/api/public/leads/support",
        {
          name: form.name.trim(),
          phone: form.phone.trim(),
          estate: form.estate.trim(),
          message: form.message.trim(),
          source: "website",
        }
      );

      if (res.ok) {
        setStatus("sent");
        setForm({ name: "", phone: "", estate: "", message: "" });
      } else {
        throw new Error("Failed");
      }
    } catch (err: any) {
      setStatus("error");
      setErrorMsg(err?.message || "Something went wrong");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="section-pad bg-white">
      <div className="container-page max-w-2xl">
        <h1 className="text-3xl font-extrabold text-[var(--navy)]">
          Support Request
        </h1>
        <p className="mt-2 text-black/60">
          Having issues? Let us know and we’ll assist you.
        </p>

        <form onSubmit={submit} className="mt-6 space-y-4">
          <input
            value={form.name}
            onChange={(e) => onChange("name", e.target.value)}
            placeholder="Your name"
            className="w-full px-4 py-3 border rounded-xl"
            required
          />

          <input
            value={form.phone}
            onChange={(e) => onChange("phone", e.target.value)}
            placeholder="Phone"
            className="w-full px-4 py-3 border rounded-xl"
            required
          />

          <input
            value={form.estate}
            onChange={(e) => onChange("estate", e.target.value)}
            placeholder="Estate"
            className="w-full px-4 py-3 border rounded-xl"
          />

          <textarea
            value={form.message}
            onChange={(e) => onChange("message", e.target.value)}
            placeholder="Describe your issue"
            className="w-full px-4 py-3 border rounded-xl"
            rows={4}
            required
          />

          <Button3D type="submit" disabled={loading}>
            {loading ? "Sending..." : "Submit"}
          </Button3D>

          {status === "sent" && (
            <div className="text-green-600 font-semibold">
              Request sent successfully
            </div>
          )}

          {status === "error" && (
            <div className="text-red-600 font-semibold">
              {errorMsg}
            </div>
          )}
        </form>
      </div>
    </section>
  );
}