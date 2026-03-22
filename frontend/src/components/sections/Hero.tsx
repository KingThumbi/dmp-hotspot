// src/components/sections/Hero.tsx
import { useNavigate } from "react-router-dom";
import { motion, useReducedMotion, type Variants } from "framer-motion";
import Button3D from "../ui/Button3D";
import { geometricBackground } from "../../theme/geometric";

const easeOut: [number, number, number, number] = [0.16, 1, 0.3, 1];

const fadeUp: Variants = {
  hidden: { opacity: 0, y: 14 },
  show: (delay = 0) => ({
    opacity: 1,
    y: 0,
    transition: { duration: 0.55, ease: easeOut, delay },
  }),
};

const stagger: Variants = {
  hidden: {},
  show: {
    transition: {
      staggerChildren: 0.08,
      delayChildren: 0.05,
    },
  },
};

export default function Hero() {
  const navigate = useNavigate();
  const reduceMotion = useReducedMotion();

  const motionInitial = reduceMotion ? false : "hidden";
  const motionAnimate = reduceMotion ? false : "show";

  return (
    <section className="relative overflow-hidden" style={{ background: geometricBackground }}>
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -top-24 -left-24 h-80 w-80 rounded-full bg-[var(--gold)] blur-2xl opacity-15" />
        <div className="absolute -bottom-24 -right-24 h-80 w-80 rounded-full bg-white blur-2xl opacity-10" />

        <div
          className="absolute inset-0 opacity-25"
          style={{
            backgroundImage:
              "linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)",
            backgroundSize: "52px 52px",
          }}
        />

        {/* Stronger overlay so text is always readable */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/25 via-black/45 to-black/65" />
      </div>

      <div className="container">
        {/* premium hero height (not full-screen) */}
        <div className="py-16 md:py-24 grid lg:grid-cols-2 gap-10 items-center">
          {/* LEFT */}
          <motion.div
            className="text-white"
            variants={reduceMotion ? undefined : stagger}
            initial={motionInitial}
            animate={motionAnimate}
          >
            <motion.div variants={fadeUp} custom={0}>
              <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/10 border border-white/15 backdrop-blur">
                <span className="h-2 w-2 rounded-full bg-[var(--gold)]" />
                <span className="text-sm font-semibold text-white/90">
                  Bold Modern ISP • Nairobi, Kenya
                </span>
              </div>
            </motion.div>

            <motion.h1
              variants={fadeUp}
              custom={0.08}
              className="mt-7 text-5xl md:text-7xl font-black leading-[1.05] tracking-tight"
            >
              Internet That <span className="text-[var(--gold)]">Just Works</span>
              <span className="text-[var(--gold)]">.</span>
              <br />
              Built for Homes & Businesses
            </motion.h1>

            <motion.p
              variants={fadeUp}
              custom={0.16}
              className="mt-6 text-lg md:text-xl text-white/85 max-w-xl leading-relaxed"
            >
              Fast installs, stable speeds, and support you can actually reach — built like a technology
              company, not just “bandwidth.”
            </motion.p>

            <motion.div variants={fadeUp} custom={0.24} className="mt-9 flex flex-col sm:flex-row gap-4">
              <Button3D onClick={() => navigate("/packages")}>View Packages</Button3D>

              <button
                onClick={() => navigate("/coverage")}
                className="
                  px-6 py-3 rounded-xl font-extrabold
                  border border-white/25 text-white
                  bg-white/10 backdrop-blur
                  transition-transform duration-150
                  hover:-translate-y-1 hover:bg-white/15
                  active:translate-y-0
                  focus:outline-none focus:ring-4 focus:ring-white/10
                "
              >
                Check Coverage
              </button>
            </motion.div>

            <motion.div
              variants={fadeUp}
              custom={0.32}
              className="mt-10 grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl"
            >
              {[
                { k: "Fast Setup", v: "Quick installs & activation" },
                { k: "Support", v: "Call / WhatsApp ready" },
                { k: "Secure", v: "Protected network design" },
              ].map((x) => (
                <div key={x.k} className="rounded-2xl bg-white/10 border border-white/15 p-4 backdrop-blur">
                  <div className="text-[var(--gold)] font-black">{x.k}</div>
                  <div className="text-xs text-white/80 mt-1">{x.v}</div>
                </div>
              ))}
            </motion.div>
          </motion.div>

          {/* RIGHT */}
          <motion.div initial={motionInitial} animate={motionAnimate} variants={fadeUp} custom={0.12} className="relative">
            <div className="pointer-events-none absolute -top-6 -right-6 h-24 w-24 rounded-2xl bg-[var(--gold)]/20 blur-xl" />

            <div className="rounded-3xl bg-white/10 border border-white/15 p-6 backdrop-blur-md shadow-2xl">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-white font-extrabold text-lg">Quick Start</div>
                  <div className="text-white/80 text-sm mt-1">Get connected in 3 simple steps.</div>
                </div>

                <div className="rounded-2xl bg-white/10 border border-white/10 px-3 py-2 text-xs text-white/85">
                  M-Pesa Ready
                </div>
              </div>

              <div className="mt-6 space-y-3">
                {[
                  { n: "1", t: "Choose a package", d: "Residential or Hotspot" },
                  { n: "2", t: "Confirm coverage", d: "Share your estate/location" },
                  { n: "3", t: "Install & go live", d: "Stable internet activated" },
                ].map((s) => (
                  <div key={s.n} className="rounded-2xl bg-white/10 border border-white/10 p-4 flex gap-3">
                    <div className="h-10 w-10 rounded-xl bg-[var(--gold)] text-black font-black flex items-center justify-center">
                      {s.n}
                    </div>

                    <div className="min-w-0">
                      <div className="text-white font-extrabold">{s.t}</div>
                      <div className="text-xs text-white/75 mt-1">{s.d}</div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-6 flex flex-col sm:flex-row gap-3">
                <Button3D className="w-full" onClick={() => navigate("/contact")}>
                  Talk to Sales
                </Button3D>

                <button
                  onClick={() => navigate("/packages")}
                  className="
                    w-full px-6 py-3 rounded-xl font-extrabold
                    border border-white/25 text-white
                    bg-white/10 backdrop-blur
                    transition-transform duration-150
                    hover:-translate-y-1 hover:bg-white/15
                    active:translate-y-0
                  "
                >
                  Pick a Plan
                </button>
              </div>

              <div className="mt-5 text-xs text-white/65">
                Tip: Start with 7Mbps or 20Mbps for the best everyday experience.
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
