import type { ReactNode } from "react";
import { Link } from "react-router-dom";

type QuickStat = {
  label: string;
  value: string;
};

type TopLink = {
  to: string;
  label: string;
  variant?: "primary" | "secondary";
};

type LegalPageLayoutProps = {
  badge?: string;
  title: string;
  description: string;
  effectiveDate: string;
  company?: string;
  website?: string;
  quickStats?: QuickStat[];
  topLinks?: TopLink[];
  children: ReactNode;
};

export function LegalSection({
  id,
  title,
  children,
}: {
  id: string;
  title: string;
  children: ReactNode;
}) {
  return (
    <section
      id={id}
      className="rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-[0_10px_40px_rgba(0,0,0,0.25)] backdrop-blur-sm md:p-8"
    >
      <h2 className="text-xl font-bold tracking-tight text-white md:text-2xl">
        {title}
      </h2>

      <div className="mt-4 space-y-4 text-sm leading-7 text-slate-300 md:text-base">
        {children}
      </div>
    </section>
  );
}

export function LegalBulletList({ items }: { items: string[] }) {
  return (
    <ul className="space-y-3">
      {items.map((item) => (
        <li key={item} className="flex items-start gap-3">
          <span className="mt-2 h-2 w-2 shrink-0 rounded-full bg-yellow-400" />
          <span>{item}</span>
        </li>
      ))}
    </ul>
  );
}

export function LegalContactCard() {
  return (
    <div className="rounded-2xl border border-white/10 bg-slate-900/70 p-5">
      <p className="text-lg font-semibold text-white">Dmpolin Connect</p>
      <div className="mt-3 space-y-2 text-slate-300">
        <p>
          Email:{" "}
          <a
            href="mailto:support@dmpolinconnect.co.ke"
            className="text-yellow-300 hover:text-yellow-200"
          >
            support@dmpolinconnect.co.ke
          </a>
        </p>
        <p>
          Website:{" "}
          <a
            href="https://www.dmpolinconnect.co.ke"
            className="text-yellow-300 hover:text-yellow-200"
            target="_blank"
            rel="noreferrer"
          >
            www.dmpolinconnect.co.ke
          </a>
        </p>
      </div>
    </div>
  );
}

export default function LegalPageLayout({
  badge = "Dmpolin Connect Legal",
  title,
  description,
  effectiveDate,
  company = "Dmpolin Connect",
  website = "dmpolinconnect.co.ke",
  quickStats = [],
  topLinks = [],
  children,
}: LegalPageLayoutProps) {
  return (
    <main className="min-h-screen bg-slate-950 text-white">
      <section className="relative overflow-hidden border-b border-yellow-500/10 bg-gradient-to-b from-[#000080] via-slate-950 to-slate-950">
        <div className="absolute inset-0">
          <div className="absolute left-1/2 top-0 h-64 w-64 -translate-x-1/2 rounded-full bg-yellow-400/10 blur-3xl" />
          <div className="absolute -left-12 top-24 h-48 w-48 rounded-full bg-blue-400/10 blur-3xl" />
          <div className="absolute bottom-0 right-0 h-56 w-56 rounded-full bg-yellow-300/10 blur-3xl" />
        </div>

        <div className="relative mx-auto max-w-5xl px-6 py-16 md:px-8 md:py-20">
          <div className="inline-flex items-center rounded-full border border-yellow-400/20 bg-yellow-400/10 px-4 py-1.5 text-sm font-medium text-yellow-300">
            {badge}
          </div>

          <h1 className="mt-6 max-w-3xl text-4xl font-black tracking-tight text-white md:text-5xl">
            {title}
          </h1>

          <p className="mt-5 max-w-3xl text-base leading-8 text-slate-300 md:text-lg">
            {description}
          </p>

          <div className="mt-8 flex flex-wrap gap-3 text-sm">
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Effective Date: {effectiveDate}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Company: {company}
            </span>
            <span className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-slate-200">
              Website: {website}
            </span>
          </div>

          {topLinks.length > 0 && (
            <div className="mt-8 flex flex-wrap gap-4">
              {topLinks.map((link) => (
                <Link
                  key={`${link.to}-${link.label}`}
                  to={link.to}
                  className={
                    link.variant === "secondary"
                      ? "inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/5 px-5 py-3 font-semibold text-white transition hover:bg-white/10"
                      : "inline-flex items-center justify-center rounded-2xl bg-yellow-400 px-5 py-3 font-semibold text-slate-950 transition hover:scale-[1.02] hover:bg-yellow-300"
                  }
                >
                  {link.label}
                </Link>
              ))}
            </div>
          )}
        </div>
      </section>

      {quickStats.length > 0 && (
        <section className="mx-auto max-w-5xl px-6 py-10 md:px-8 md:py-14">
          <div
            className={`grid gap-4 rounded-3xl border border-yellow-500/10 bg-gradient-to-r from-yellow-400/10 to-white/[0.03] p-5 md:p-6 ${
              quickStats.length === 1
                ? "md:grid-cols-1"
                : quickStats.length === 2
                ? "md:grid-cols-2"
                : "md:grid-cols-3"
            }`}
          >
            {quickStats.map((stat) => (
              <div key={stat.label}>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-yellow-300">
                  {stat.label}
                </p>
                <p className="mt-2 text-sm leading-7 text-slate-300">
                  {stat.value}
                </p>
              </div>
            ))}
          </div>
        </section>
      )}

      <section className="mx-auto max-w-5xl px-6 pb-16 md:px-8 md:pb-20">
        <div className="grid gap-6">{children}</div>
      </section>
    </main>
  );
}