// src/components/sections/TestimonialsStrip.tsx
import { useEffect, useMemo, useRef, useState } from "react";
import {
  motion,
  AnimatePresence,
  useReducedMotion,
  type Variants,
} from "framer-motion";

type Testimonial = {
  quote: string;
  name: string;
  tag: string;
  area?: string;
  isLocalGuide?: boolean;
  timeAgo?: string; // e.g. "2 weeks ago"
  reviewCount?: number; // e.g. 37
  rating?: 4 | 5;
};

const items: Testimonial[] = [
  {
    quote:
      "Stable speeds and quick support. Install was smooth and the team was responsive.",
    name: "Wanjiku N.",
    tag: "Residential",
    area: "Roysambu",
    isLocalGuide: true,
    timeAgo: "2 weeks ago",
    reviewCount: 37,
    rating: 5,
  },
  {
    quote:
      "Reliable connection for our daily operations. Great value for the speed tier we picked.",
    name: "Kevin Omosh",
    tag: "Business",
    area: "Kasarani",
    isLocalGuide: false,
    timeAgo: "1 month ago",
    reviewCount: 102,
    rating: 5,
  },
  {
    quote:
      "Hotspot bundles are super convenient. Payments are easy and access is instant.",
    name: "Aisha M.",
    tag: "Hotspot",
    area: "Githurai",
    isLocalGuide: true,
    timeAgo: "5 days ago",
    reviewCount: 58,
    rating: 5,
  },
  {
    quote:
      "Setup was fast and service is steady. Exactly what we needed at home.",
    name: "Rahul Patel",
    tag: "Residential",
    area: "Mirema",
    isLocalGuide: true,
    timeAgo: "3 weeks ago",
    reviewCount: 24,
    rating: 5,
  },
];

function clampIndex(i: number, len: number) {
  const m = i % len;
  return m < 0 ? m + len : m;
}

function StarsRow({ rating = 5 }: { rating?: 4 | 5 }) {
  return (
    <div
      className="flex items-center gap-0.5 text-[var(--gold)]"
      aria-label={`${rating} star rating`}
    >
      {Array.from({ length: 5 }).map((_, i) => (
        <span
          key={i}
          className={[
            "font-black leading-none",
            i < rating ? "" : "opacity-25",
          ].join(" ")}
        >
          ★
        </span>
      ))}
    </div>
  );
}

function GoogleBadge() {
  // Minimal “review style” pill (no logo usage)
  return (
    <div className="inline-flex items-center gap-2 rounded-full border border-black/10 bg-white px-3 py-1 text-xs font-extrabold text-black shadow-sm">
      <span className="h-2 w-2 rounded-full bg-[var(--navy)]/70" />
      Reviews
    </div>
  );
}

function LocalGuideBadge() {
  return (
    <span className="inline-flex items-center gap-1 rounded-full bg-[var(--navy)]/10 text-[var(--navy)] px-2 py-0.5 text-[11px] font-extrabold">
      <span className="h-1.5 w-1.5 rounded-full bg-[var(--navy)]" />
      Local Guide
    </span>
  );
}

function Avatar({ name }: { name: string }) {
  // Inline SVG silhouette (neutral “photo placeholder” feel)
  const silhouetteSvg = encodeURIComponent(`
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
      <defs>
        <radialGradient id="g" cx="30%" cy="20%" r="80%">
          <stop offset="0%" stop-color="#ffffff" stop-opacity="0.55"/>
          <stop offset="55%" stop-color="#ffffff" stop-opacity="0.15"/>
          <stop offset="100%" stop-color="#000000" stop-opacity="0.08"/>
        </radialGradient>
      </defs>
      <rect width="64" height="64" rx="32" fill="url(#g)"/>
      <circle cx="32" cy="25" r="12" fill="rgba(10,10,18,0.45)"/>
      <path d="M14 54c2-12 14-17 18-17s16 5 18 17" fill="rgba(10,10,18,0.45)"/>
    </svg>
  `);

  return (
    <div className="relative">
      <div
        className="h-11 w-11 rounded-full border border-black/10 shadow-sm bg-[var(--gray-light)] overflow-hidden"
        style={{
          backgroundImage: `url("data:image/svg+xml,${silhouetteSvg}")`,
          backgroundSize: "cover",
          backgroundPosition: "center",
        }}
        aria-label={`Reviewer avatar for ${name}`}
        title={name}
      />
      <div className="pointer-events-none absolute -inset-1 rounded-full border border-[var(--gold)]/35" />
    </div>
  );
}

export default function TestimonialsStrip() {
  const reduceMotion = useReducedMotion();
  const [index, setIndex] = useState(0);
  const [dir, setDir] = useState<1 | -1>(1);
  const [paused, setPaused] = useState(false);
  const timerRef = useRef<number | null>(null);

  const active = useMemo(
    () => items[clampIndex(index, items.length)],
    [index]
  );

  function go(step: number, direction: 1 | -1) {
    setDir(direction);
    setIndex((prev) => clampIndex(prev + step, items.length));
  }

  function next() {
    go(1, 1);
  }

  function prev() {
    go(-1, -1);
  }

  // Auto-rotate (pause on hover + pause when tab hidden)
  useEffect(() => {
    function clear() {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    }

    function start() {
      clear();
      if (paused) return;

      timerRef.current = window.setInterval(() => {
        setDir(1);
        setIndex((prev) => clampIndex(prev + 1, items.length));
      }, 5200);
    }

    function onVis() {
      if (document.hidden) clear();
      else start();
    }

    start();
    document.addEventListener("visibilitychange", onVis);
    return () => {
      clear();
      document.removeEventListener("visibilitychange", onVis);
    };
  }, [paused]);

  // Framer Motion v12 TS-safe easing (no string easings)
  const easeOut: [number, number, number, number] = [0.16, 1, 0.3, 1];
  const easeIn: [number, number, number, number] = [0.7, 0, 0.84, 0];

  const variants: Variants = {
    enter: (d: 1 | -1) => ({
      x: reduceMotion ? 0 : d > 0 ? 28 : -28,
      opacity: 0,
      filter: "blur(2px)",
    }),
    center: {
      x: 0,
      opacity: 1,
      filter: "blur(0px)",
      transition: { duration: reduceMotion ? 0 : 0.28, ease: easeOut },
    },
    exit: (d: 1 | -1) => ({
      x: reduceMotion ? 0 : d > 0 ? -28 : 28,
      opacity: 0,
      filter: "blur(2px)",
      transition: { duration: reduceMotion ? 0 : 0.22, ease: easeIn },
    }),
  };

  const current = clampIndex(index, items.length);

  return (
    <section className="section bg-white">
      <div className="container">
        <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <h2 className="h2">What clients say</h2>
            <p className="p max-w-2xl">
              Startup-grade service delivery: fast installs, stable speeds,
              responsive support.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={prev}
              className="h-10 w-10 rounded-xl border border-black/10 bg-white shadow-sm hover:shadow-md transition active:scale-[0.98]"
              aria-label="Previous testimonial"
              type="button"
            >
              ←
            </button>
            <button
              onClick={next}
              className="h-10 w-10 rounded-xl border border-black/10 bg-white shadow-sm hover:shadow-md transition active:scale-[0.98]"
              aria-label="Next testimonial"
              type="button"
            >
              →
            </button>
          </div>
        </div>

        {/* Carousel */}
        <div className="mt-10">
          <div
            className="card card-hover p-0 overflow-hidden"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            {/* top strip */}
            <div className="px-6 md:px-8 py-5 border-b border-black/5 bg-[var(--gray-light)] flex items-center justify-between gap-4">
              <div className="flex items-center gap-3">
                <GoogleBadge />
                <div className="hidden sm:block text-xs font-bold text-black/50">
                  • Auto-rotating • pause on hover
                </div>
              </div>

              <div className="text-xs font-extrabold text-black/45">
                {current + 1} / {items.length}
              </div>
            </div>

            <div className="px-6 md:px-8 py-8 relative">
              <AnimatePresence mode="wait" custom={dir}>
                <motion.div
                  key={active.name + active.tag + active.quote}
                  custom={dir}
                  variants={variants}
                  initial="enter"
                  animate="center"
                  exit="exit"
                  className="grid md:grid-cols-[1fr_auto] gap-8 items-start"
                  drag={reduceMotion ? false : "x"}
                  dragConstraints={{ left: 0, right: 0 }}
                  dragElastic={0.12}
                  onDragEnd={(_, info) => {
                    const swipe = info.offset.x;
                    const velocity = info.velocity.x;
                    const strength =
                      Math.abs(swipe) + Math.abs(velocity) * 0.2;

                    if (strength > 120) {
                      if (swipe < 0) next();
                      else prev();
                    }
                  }}
                >
                  {/* Quote */}
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <div className="text-xs font-black text-[var(--navy)]">
                        {active.tag}
                        {active.area ? ` • ${active.area}` : ""}
                      </div>

                      {active.isLocalGuide && <LocalGuideBadge />}

                      {active.timeAgo && (
                        <div className="text-xs font-bold text-black/45">
                          • {active.timeAgo}
                        </div>
                      )}
                    </div>

                    <div className="mt-4 text-lg md:text-xl font-semibold text-black/80 leading-relaxed">
                      “{active.quote}”
                    </div>

                    <div className="mt-6 flex flex-wrap items-center gap-3">
                      <StarsRow rating={active.rating ?? 5} />
                      <div className="text-xs font-bold text-black/50">
                        Posted publicly
                      </div>
                    </div>
                  </div>

                  {/* Profile */}
                  <div className="md:text-right flex md:flex-col items-center md:items-end gap-4">
                    <Avatar name={active.name} />
                    <div className="min-w-0">
                      <div className="font-extrabold text-black">
                        {active.name}
                      </div>
                      <div className="text-sm text-black/55">
                        {active.isLocalGuide ? "Local Guide" : "Customer"}
                        {typeof active.reviewCount === "number"
                          ? ` · ${active.reviewCount} reviews`
                          : ""}
                      </div>
                    </div>
                  </div>
                </motion.div>
              </AnimatePresence>

              {/* Dots */}
              <div className="mt-8 flex items-center justify-center gap-2">
                {items.map((_, i) => {
                  const isActive = i === current;
                  return (
                    <button
                      key={i}
                      type="button"
                      onClick={() => {
                        setDir(i > current ? 1 : -1);
                        setIndex(i);
                      }}
                      className={[
                        "h-2.5 rounded-full transition",
                        isActive
                          ? "w-8 bg-[var(--navy)]"
                          : "w-2.5 bg-black/15 hover:bg-black/25",
                      ].join(" ")}
                      aria-label={`Go to testimonial ${i + 1}`}
                    />
                  );
                })}
              </div>

              <div className="mt-5 text-center text-xs text-black/45">
                Tip: Swipe left/right on mobile.
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
