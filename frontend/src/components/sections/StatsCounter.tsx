// src/components/sections/StatsCounter.tsx
import { useEffect, useState } from "react";

function useCountUp(target: number, durationMs = 1000) {
  const [value, setValue] = useState(0);

  useEffect(() => {
    const start = performance.now();
    let raf = 0;

    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / durationMs);
      const eased = 1 - Math.pow(1 - p, 3);
      setValue(Math.round(target * eased));
      if (p < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return value;
}

function Stat({ value, suffix, label }: any) {
  const n = useCountUp(value);

  return (
    <div className="card card-hover p-8 text-center">
      <div className="text-4xl font-black text-[var(--navy)]">
        {n}
        <span className="text-[var(--gold)] ml-1">{suffix}</span>
      </div>
      <div className="mt-3 text-sm font-semibold text-black/70">
        {label}
      </div>
    </div>
  );
}

export default function StatsCounter() {
  return (
    <section className="section section-muted">
      <div className="container">
        <div className="text-center max-w-2xl mx-auto">
          <h2 className="h2">
            Built for stability & scale<span className="text-[var(--gold)]">.</span>
          </h2>
          <p className="p">
            We design connectivity, payments, automation, and systems that are
            engineered for reliability.
          </p>
        </div>

        <div className="mt-12 grid sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <Stat value={24} suffix="hrs" label="Average Setup Time" />
          <Stat value={3} suffix="+" label="Support Channels" />
          <Stat value={99} suffix="%" label="Uptime Mindset" />
          <Stat value={12} suffix="mo" label="Growth Roadmap" />
        </div>
      </div>
    </section>
  );
}
