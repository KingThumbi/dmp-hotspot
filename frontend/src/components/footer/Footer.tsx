import { Link } from "react-router-dom";

const quickLinks = [
  { label: "Home", to: "/" },
  { label: "Packages", to: "/packages" },
  { label: "Coverage", to: "/coverage" },
  { label: "Support", to: "/support" },
  { label: "Contact", to: "/contact" },
];

const legalLinks = [
  { label: "Terms & Conditions", to: "/terms" },
  { label: "Privacy Policy", to: "/privacy" },
  { label: "Acceptable Use Policy", to: "/acceptable-use" },
  { label: "Refund Policy", to: "/refund-policy" },
  { label: "Service Level Agreement", to: "/service-level-agreement" },
];

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="relative overflow-hidden border-t border-white/10 bg-slate-950 text-white">
      {/* Accent line */}
      <div className="h-1 w-full bg-gradient-to-r from-[var(--navy)] via-[var(--gold)] to-[var(--navy)]" />

      {/* Background effects */}
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute left-0 top-0 h-72 w-72 rounded-full bg-[var(--navy)]/20 blur-3xl" />
        <div className="absolute bottom-0 right-0 h-80 w-80 rounded-full bg-[var(--gold)]/10 blur-3xl" />
        <div className="absolute left-1/2 top-24 h-56 w-56 -translate-x-1/2 rounded-full bg-white/5 blur-3xl" />
      </div>

      <div className="relative mx-auto max-w-7xl px-6 py-16 md:px-8 lg:px-10">
        {/* Top CTA band */}
        <div className="mb-12 rounded-3xl border border-white/10 bg-white/[0.04] p-6 shadow-[0_10px_40px_rgba(0,0,0,0.25)] backdrop-blur-sm md:flex md:items-center md:justify-between md:p-8">
          <div className="max-w-2xl">
            <p className="text-xs font-black uppercase tracking-[0.22em] text-yellow-300">
              Dmpolin Connect
            </p>
            <h2 className="mt-3 text-2xl font-black tracking-tight text-white md:text-3xl">
              Reliable internet for homes, businesses, and hotspot users
            </h2>
            <p className="mt-3 text-sm leading-7 text-slate-300 md:text-base">
              Fast installs, M-Pesa payments, responsive support, and a growing
              network built to keep Nairobi connected.
            </p>
          </div>

          <div className="mt-6 flex flex-wrap gap-3 md:mt-0 md:justify-end">
            <Link
              to="/packages"
              className="inline-flex items-center justify-center rounded-2xl bg-[var(--gold)] px-5 py-3 font-semibold text-slate-950 transition hover:scale-[1.02] hover:opacity-95"
            >
              View Packages
            </Link>
            <Link
              to="/contact"
              className="inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/5 px-5 py-3 font-semibold text-white transition hover:bg-white/10"
            >
              Contact Us
            </Link>
          </div>
        </div>

        {/* Main footer grid */}
        <div className="grid gap-10 md:grid-cols-2 xl:grid-cols-4">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-[var(--gold)] text-lg font-black text-slate-950 shadow-lg shadow-yellow-500/20">
                D
              </div>

              <div>
                <p className="text-lg font-black tracking-tight text-white">
                  Dmpolin Connect
                </p>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
                  Modern ISP • Nairobi, Kenya
                </p>
              </div>
            </div>

            <p className="mt-5 max-w-sm text-sm leading-7 text-slate-300">
              A technology-forward internet service provider delivering reliable
              broadband, hotspot bundles, and scalable digital connectivity for
              homes and businesses.
            </p>

            <div className="mt-6 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-xs font-bold text-slate-200">
              <span className="h-2 w-2 rounded-full bg-[var(--gold)]" />
              M-Pesa supported • Fast installs
            </div>
          </div>

          {/* Quick links */}
          <div>
            <h3 className="text-sm font-black uppercase tracking-[0.18em] text-yellow-300">
              Quick Links
            </h3>

            <ul className="mt-5 space-y-3">
              {quickLinks.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className="text-sm font-medium text-slate-300 transition hover:translate-x-1 hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <h3 className="text-sm font-black uppercase tracking-[0.18em] text-yellow-300">
              Contact
            </h3>

            <div className="mt-5 space-y-5 text-sm text-slate-300">
              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">
                  Call
                </p>
                <div className="mt-2 space-y-2">
                  <a
                    href="tel:+254780912362"
                    className="block font-semibold transition hover:text-white"
                  >
                    0780 912 362
                  </a>
                  <a
                    href="tel:+254731912362"
                    className="block font-semibold transition hover:text-white"
                  >
                    0731 912 362
                  </a>
                </div>
              </div>

              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">
                  WhatsApp
                </p>
                <a
                  href="https://wa.me/254780912362"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-2 font-semibold transition hover:text-white"
                >
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  Chat on WhatsApp
                </a>
              </div>

              <div>
                <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">
                  Email
                </p>
                <a
                  href="mailto:support@dmpolinconnect.co.ke"
                  className="mt-2 block font-semibold transition hover:text-white"
                >
                  support@dmpolinconnect.co.ke
                </a>
              </div>
            </div>
          </div>

          {/* Legal */}
          <div>
            <h3 className="text-sm font-black uppercase tracking-[0.18em] text-yellow-300">
              Legal
            </h3>

            <ul className="mt-5 space-y-3">
              {legalLinks.map((item) => (
                <li key={item.to}>
                  <Link
                    to={item.to}
                    className="text-sm font-medium text-slate-300 transition hover:translate-x-1 hover:text-white"
                  >
                    {item.label}
                  </Link>
                </li>
              ))}
            </ul>

            <div className="mt-6 rounded-2xl border border-white/10 bg-white/[0.04] p-4">
              <p className="text-xs font-black uppercase tracking-[0.16em] text-slate-500">
                Support Hours
              </p>
              <p className="mt-2 text-sm font-semibold text-white">
                Monday – Saturday • 8:00am – 6:00pm
              </p>
              <p className="mt-1 text-xs leading-6 text-slate-400">
                Urgent assistance is also available through WhatsApp.
              </p>
            </div>
          </div>
        </div>

        {/* Bottom strip */}
        <div className="mt-12 border-t border-white/10 pt-6">
          <div className="flex flex-col gap-3 text-sm text-slate-400 md:flex-row md:items-center md:justify-between">
            <p>© {year} Dmpolin Connect. All rights reserved.</p>
            <p className="font-semibold tracking-wide text-slate-300">
              For Connections Beyond the Horizon
            </p>
          </div>
        </div>
      </div>
    </footer>
  );
}