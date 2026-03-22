// src/components/sections/PackagesPreview.tsx
import { useMemo } from "react";
import { useNavigate } from "react-router-dom";
import Button3D from "../ui/Button3D";

function formatKes(n: number) {
  return `KES ${n.toLocaleString("en-KE")}`;
}

type MiniCardProps = {
  title: string;
  subtitle: string;
  price: number;
  badge?: string;
  bestFor?: string;
  meta?: string;
  onClick?: () => void;
};

function MiniCard({
  title,
  subtitle,
  price,
  badge,
  bestFor = "Everyday use",
  meta = "M-Pesa supported",
  onClick,
}: MiniCardProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="
        group relative text-left w-full
        rounded-3xl bg-white border border-black/5 shadow-lg
        p-6 overflow-hidden
        transition-all duration-200
        hover:-translate-y-1 hover:shadow-2xl
        focus:outline-none focus:ring-4 focus:ring-[var(--gold)]/25
      "
      aria-label={`View ${title} package`}
    >
      {/* Hover glow blob */}
      <div
        className="
          pointer-events-none absolute -top-28 -right-28 h-64 w-64 rounded-full
          bg-[var(--gold)]/0 blur-3xl
          transition duration-300
          group-hover:bg-[var(--gold)]/18
        "
      />

      {/* Premium shine sweep */}
      <div
        className="
          pointer-events-none absolute inset-0 opacity-0
          bg-gradient-to-r from-transparent via-white/45 to-transparent
          translate-x-[-140%]
          transition-all duration-700
          group-hover:opacity-100 group-hover:translate-x-[140%]
        "
      />

      {/* Subtle grid texture */}
      <div
        className="
          pointer-events-none absolute inset-0 opacity-0
          transition duration-200
          group-hover:opacity-100
        "
        style={{
          backgroundImage:
            "linear-gradient(to right, rgba(0,0,0,0.05) 1px, transparent 1px), linear-gradient(to bottom, rgba(0,0,0,0.05) 1px, transparent 1px)",
          backgroundSize: "36px 36px",
          maskImage:
            "radial-gradient(circle at 50% 20%, rgba(0,0,0,0.9), transparent 55%)",
          WebkitMaskImage:
            "radial-gradient(circle at 50% 20%, rgba(0,0,0,0.9), transparent 55%)",
        }}
      />

      {/* Premium hover ring */}
      <div
        className="
          pointer-events-none absolute inset-0 rounded-3xl
          ring-1 ring-black/5
          transition duration-200
          group-hover:ring-[var(--gold)]/40
        "
      />

      <div className="relative">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="text-[var(--navy)] font-black text-lg truncate">
              {title}
            </div>
            <div className="text-sm text-black/60 mt-1">{subtitle}</div>
          </div>

          {badge ? (
            <div
              className="
                shrink-0 text-xs font-black px-3 py-1 rounded-full
                bg-[var(--navy)] text-white shadow-sm
                transition-transform duration-200
                group-hover:scale-[1.03]
              "
            >
              {badge}
            </div>
          ) : null}
        </div>

        <div className="mt-5">
          <div className="text-2xl font-black text-black">
            {formatKes(price)}
            <span className="text-xs font-semibold text-black/45 ml-2">
              / month
            </span>
          </div>
          <div className="text-xs text-black/50 mt-1">{meta}</div>
        </div>

        <div className="mt-6 flex items-center justify-between gap-4">
          <div className="text-xs font-semibold text-black/55">
            Best for: <span className="text-black/75">{bestFor}</span>
          </div>

          <div className="flex items-center gap-2">
            <span
              className="
                text-sm font-extrabold text-[var(--navy)]
                transition group-hover:text-[var(--gold)]
              "
            >
              View
            </span>
            <span
              className="
                text-[var(--navy)] transition
                group-hover:text-[var(--gold)] group-hover:translate-x-0.5
              "
            >
              →
            </span>
          </div>
        </div>

        {/* Hover-only CTA (desktop) */}
        <div
          className="
            mt-5 hidden md:flex items-center justify-between gap-3
            opacity-0 translate-y-2
            transition duration-200
            group-hover:opacity-100 group-hover:translate-y-0
          "
        >
          <div className="text-xs font-semibold text-black/50">
            Instant support via WhatsApp
          </div>
          <div
            className="
              inline-flex items-center gap-2
              text-xs font-black
              rounded-full px-3 py-2
              bg-[var(--gray-light)] border border-black/5
            "
          >
            <span className="h-2 w-2 rounded-full bg-[var(--gold)]" />
            Recommended
          </div>
        </div>
      </div>
    </button>
  );
}

export default function PackagesPreview() {
  const navigate = useNavigate();

  const residential = useMemo(
    () => [
      {
        title: "7 Mbps",
        subtitle: "Great for a small home",
        price: 1500,
        badge: "Popular",
        bestFor: "Browsing + streaming",
      },
      {
        title: "20 Mbps",
        subtitle: "Streaming + multiple devices",
        price: 2500,
        badge: "Best fit",
        bestFor: "Families + work",
      },
      {
        title: "30 Mbps",
        subtitle: "Heavy usage + fast downloads",
        price: 3000,
        badge: "Top tier",
        bestFor: "Power users",
      },
    ],
    []
  );

  const hotspot = useMemo(
    () => [
      {
        title: "1 User • Daily",
        subtitle: "Quick access",
        price: 50,
        bestFor: "Single device",
        meta: "Instant login access",
      },
      {
        title: "2 Users • Weekly",
        subtitle: "Couples / small use",
        price: 160,
        badge: "Value",
        bestFor: "Two devices",
        meta: "Best for shared use",
      },
      {
        title: "5 Users • Monthly",
        subtitle: "Small group bundle",
        price: 900,
        badge: "Best value",
        bestFor: "Group access",
        meta: "Great for small teams",
      },
    ],
    []
  );

  return (
    <section className="section section-muted">
      <div className="container">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h2 className="h2">Packages</h2>
            <p className="p max-w-2xl">
              Simple, affordable internet packages for homes and hotspot users — built for stability and support.
            </p>
          </div>

          <div className="flex gap-3">
            <Button3D onClick={() => navigate("/packages")}>
              View All Packages
            </Button3D>
          </div>
        </div>

        {/* Residential */}
        <div className="mt-10">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-xl font-black text-black">
              Residential (Home Internet)
            </h3>
            <button
              type="button"
              onClick={() => navigate("/packages")}
              className="text-sm font-extrabold text-[var(--navy)] hover:text-[var(--gold)] transition"
            >
              See more →
            </button>
          </div>

          <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {residential.map((p) => (
              <MiniCard
                key={p.title}
                {...p}
                onClick={() => navigate("/packages")}
              />
            ))}
          </div>
        </div>

        {/* Hotspot */}
        <div className="mt-12">
          <div className="flex items-center justify-between gap-4">
            <h3 className="text-xl font-black text-black">Hotspot Bundles</h3>
            <button
              type="button"
              onClick={() => navigate("/packages")}
              className="text-sm font-extrabold text-[var(--navy)] hover:text-[var(--gold)] transition"
            >
              See more →
            </button>
          </div>

          <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {hotspot.map((p) => (
              <MiniCard
                key={p.title}
                {...p}
                onClick={() => navigate("/packages")}
              />
            ))}
          </div>
        </div>

        {/* CTA strip */}
        <div className="mt-12 rounded-3xl bg-[var(--navy)] text-white px-6 py-8 md:px-10 md:py-10 shadow-2xl relative overflow-hidden">
          {/* CTA glow */}
          <div className="pointer-events-none absolute -top-24 -left-24 h-72 w-72 rounded-full bg-[var(--gold)]/20 blur-3xl" />
          <div className="pointer-events-none absolute -bottom-24 -right-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />

          <div className="relative flex flex-col md:flex-row md:items-center md:justify-between gap-6">
            <div>
              <div className="text-2xl md:text-3xl font-black">
                Ready to get connected<span className="text-[var(--gold)]">?</span>
              </div>
              <div className="text-white/80 mt-2">
                Choose a plan, confirm coverage, and we’ll get you online fast.
              </div>
            </div>

            <div className="flex flex-col sm:flex-row gap-3">
              <Button3D onClick={() => navigate("/packages")}>Subscribe Now</Button3D>
              <button
                type="button"
                onClick={() => navigate("/contact")}
                className="
                  px-6 py-3 rounded-xl font-extrabold
                  border border-white/25 text-white bg-white/10 backdrop-blur
                  transition transform hover:-translate-y-1 hover:bg-white/15 active:translate-y-0
                "
              >
                Talk to Sales
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
