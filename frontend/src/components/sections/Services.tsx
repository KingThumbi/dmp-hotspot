import { motion } from "framer-motion";
import Button3D from "../ui/Button3D";
import { useNavigate } from "react-router-dom";

const services = [
  {
    title: "Training & Certification",
    items: ["Linux Training", "Web Design Training", "Graphics Design Training"],
    icon: "🎓",
  },
  {
    title: "Business Systems",
    items: ["POS Installation", "Custom App Creation", "Website Design & Hosting"],
    icon: "🧩",
  },
  {
    title: "Connectivity & Security",
    items: ["Internet Provision", "Networking", "CCTV Installation"],
    icon: "🛡️",
  },
];

export default function Services() {
  const navigate = useNavigate();

  return (
    <section className="section bg-white">
      <div className="container">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h2 className="h2">Digital Solutions</h2>
            <p className="p max-w-2xl">
              Beyond internet — we deploy business systems, train teams, and build digital tools that help you grow.
            </p>
          </div>

          <div className="flex gap-3">
            <Button3D onClick={() => navigate("/contact")}>Request a Quote</Button3D>
          </div>
        </div>

        <div className="mt-10 grid md:grid-cols-3 gap-6">
          {services.map((s) => (
            <motion.div
              key={s.title}
              className="card card-hover p-7 bg-[var(--gray-light)]"
              whileHover={{ y: -6 }}
              transition={{ duration: 0.18 }}
            >
              <div className="flex items-start justify-between gap-4">
                <div className="text-3xl">{s.icon}</div>

                <div className="text-xs font-black px-3 py-1 rounded-full bg-white border border-black/5 text-black/70">
                  Premium delivery
                </div>
              </div>

              <div className="mt-4 text-xl font-black text-[var(--navy)]">{s.title}</div>

              <ul className="mt-4 space-y-2 text-sm text-black/75">
                {s.items.map((it) => (
                  <li key={it} className="flex gap-2 items-start">
                    <span className="text-[var(--gold)] mt-1">●</span>
                    <span>{it}</span>
                  </li>
                ))}
              </ul>

              <div className="mt-6 flex items-center justify-between gap-4">
                <button
                  onClick={() => navigate("/contact")}
                  className="inline-flex font-black text-[var(--navy)] hover:text-[var(--gold)] transition"
                >
                  Talk to us →
                </button>

                <div className="h-10 w-10 rounded-2xl bg-white border border-black/5 flex items-center justify-center shadow-sm">
                  <span className="text-[var(--navy)] font-black">+</span>
                </div>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}
