export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="bg-white border-t border-black/5">
      {/* Accent strip (brand without killing readability) */}
      <div className="h-1 bg-[var(--navy)]" />

      <div className="container py-14">
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-10">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-3">
              <div className="h-10 w-10 rounded-2xl bg-[var(--gold)] flex items-center justify-center font-black text-black">
                D
              </div>
              <div>
                <div className="text-lg font-black text-[var(--navy)]">Dmpolin Connect</div>
                <div className="text-xs font-semibold text-black/55">Modern ISP • Nairobi, Kenya</div>
              </div>
            </div>

            <p className="mt-4 text-sm text-black/65 leading-relaxed">
              A technology-forward ISP delivering reliable broadband, hotspot bundles, and scalable digital
              infrastructure for homes and businesses.
            </p>

            <div className="mt-5 inline-flex items-center gap-2 rounded-full bg-[var(--gray-light)] border border-black/5 px-4 py-2 text-xs font-black text-black/70">
              <span className="h-2 w-2 rounded-full bg-[var(--gold)]" />
              M-Pesa supported • Fast installs
            </div>
          </div>

          {/* Quick Links */}
          <div>
            <div className="font-black text-[var(--navy)]">Quick Links</div>
            <ul className="mt-4 space-y-2 text-sm text-black/70">
              {[
                { label: "Packages", href: "/packages" },
                { label: "Coverage", href: "/coverage" },
                { label: "Shop", href: "/shop" },
                { label: "Support", href: "/support" },
                { label: "Contact", href: "/contact" },
              ].map((x) => (
                <li key={x.href}>
                  <a className="hover:text-[var(--navy)] font-semibold transition" href={x.href}>
                    {x.label}
                  </a>
                </li>
              ))}
            </ul>
          </div>

          {/* Contact */}
          <div>
            <div className="font-black text-[var(--navy)]">Contact</div>

            <div className="mt-4 space-y-4 text-sm text-black/70">
              <div>
                <div className="text-xs font-black text-black/50">Call</div>
                <div className="mt-2 space-y-1">
                  <a href="tel:+254780912362" className="block font-semibold hover:text-[var(--navy)] transition">
                    0780 912 362
                  </a>
                  <a href="tel:+254731912362" className="block font-semibold hover:text-[var(--navy)] transition">
                    0731 912 362
                  </a>
                </div>
              </div>

              <div>
                <div className="text-xs font-black text-black/50">WhatsApp</div>
                <a
                  href="https://wa.me/254780912362"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="mt-2 inline-flex items-center gap-2 font-semibold hover:text-[var(--navy)] transition"
                >
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  Chat on WhatsApp
                </a>
              </div>

              <div>
                <div className="text-xs font-black text-black/50">Email</div>
                <a
                  href="mailto:support@dmpolinconnect.co.ke"
                  className="mt-2 block font-semibold hover:text-[var(--navy)] transition"
                >
                  support@dmpolinconnect.co.ke
                </a>
              </div>
            </div>
          </div>

          {/* Legal */}
          <div>
            <div className="font-black text-[var(--navy)]">Legal</div>
            <ul className="mt-4 space-y-2 text-sm text-black/70">
              {[
                { label: "Terms", href: "/terms" },
                { label: "Privacy Policy", href: "/privacy" },
                { label: "Acceptable Use", href: "/acceptable-use" },
              ].map((x) => (
                <li key={x.href}>
                  <a className="hover:text-[var(--navy)] font-semibold transition" href={x.href}>
                    {x.label}
                  </a>
                </li>
              ))}
            </ul>

            <div className="mt-6 rounded-2xl bg-[var(--gray-light)] border border-black/5 p-4">
              <div className="text-xs font-black text-black/50">Support hours</div>
              <div className="mt-1 text-sm font-semibold text-black/70">
                Mon–Sat • 8:00am–6:00pm
              </div>
              <div className="mt-1 text-xs text-black/55">
                Emergency help available via WhatsApp.
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="mt-12 pt-6 border-t border-black/5 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-sm">
          <div className="text-black/60">© {year} Dmpolin Connect. All rights reserved.</div>
          <div className="text-black/45 font-semibold">For Connections Beyond the Horizon</div>
        </div>
      </div>
    </footer>
  );
}
