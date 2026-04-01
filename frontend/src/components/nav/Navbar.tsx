import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Button3D from "../ui/Button3D";

const navItems = [
  { to: "/", label: "Home" },
  { to: "/packages", label: "Packages" },
  { to: "/coverage", label: "Coverage" },
  { to: "/shop", label: "Shop" },
  { to: "/support", label: "Support" },
  { to: "/contact", label: "Contact" },
];

function NavItem({
  to,
  label,
  onClick,
}: {
  to: string;
  label: string;
  onClick?: () => void;
}) {
  return (
    <NavLink
      to={to}
      onClick={onClick}
      className={({ isActive }) =>
        [
          "relative rounded-xl px-3 py-2 text-sm font-semibold transition-all duration-200",
          isActive
            ? "bg-[var(--navy)]/8 text-[var(--navy)]"
            : "text-black/70 hover:bg-black/[0.04] hover:text-[var(--navy)]",
        ].join(" ")
      }
    >
      {({ isActive }) => (
        <>
          <span>{label}</span>
          {isActive && (
            <span className="absolute inset-x-3 -bottom-0.5 h-0.5 rounded-full bg-[var(--gold)]" />
          )}
        </>
      )}
    </NavLink>
  );
}

export default function Navbar() {
  const navigate = useNavigate();
  const location = useLocation();

  const [mobileOpen, setMobileOpen] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  useEffect(() => {
    setMobileOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 12);
    };

    handleScroll();
    window.addEventListener("scroll", handleScroll);
    return () => window.removeEventListener("scroll", handleScroll);
  }, []);

  useEffect(() => {
    if (!mobileOpen) return;

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [mobileOpen]);

  return (
    <>
      <header className="fixed inset-x-0 top-0 z-50">
        <div
          className={[
            "transition-all duration-300",
            scrolled
              ? "border-b border-black/10 bg-white/85 shadow-[0_10px_30px_rgba(15,23,42,0.08)] backdrop-blur-xl"
              : "border-b border-black/5 bg-white/80 backdrop-blur-xl",
          ].join(" ")}
        >
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8">
            {/* Brand */}
            <Link
              to="/"
              className="group flex items-center gap-3"
              aria-label="Dmpolin Connect home"
            >
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-[var(--gold)] font-black text-black shadow-[0_10px_25px_rgba(234,179,8,0.28)] transition-transform duration-200 group-hover:scale-[1.03]">
                D
              </div>

              <div className="min-w-0 leading-tight">
                <div className="truncate text-[var(--navy)] font-black tracking-tight">
                  Dmpolin Connect
                </div>
                <div className="hidden text-xs font-semibold text-black/50 sm:block">
                  Digital Infrastructure
                </div>
              </div>
            </Link>

            {/* Desktop navigation */}
            <nav className="hidden items-center gap-2 lg:flex">
              {navItems.map((item) => (
                <NavItem key={item.to} to={item.to} label={item.label} />
              ))}
            </nav>

            {/* Desktop CTA */}
            <div className="hidden items-center gap-3 lg:flex">
              <button
                onClick={() => navigate("/contact")}
                className="rounded-2xl border border-black/10 bg-white px-4 py-2.5 text-sm font-semibold text-black/75 transition hover:border-[var(--navy)]/15 hover:text-[var(--navy)]"
              >
                Talk to Us
              </button>

              <Button3D onClick={() => navigate("/packages")}>
                Get Connected
              </Button3D>
            </div>

            {/* Mobile action */}
            <div className="flex items-center gap-2 lg:hidden">
              <button
                onClick={() => navigate("/packages")}
                className="rounded-xl bg-[var(--navy)] px-4 py-2 text-sm font-extrabold text-white shadow-md transition hover:opacity-95"
              >
                Packages
              </button>

              <button
                type="button"
                aria-label={mobileOpen ? "Close menu" : "Open menu"}
                aria-expanded={mobileOpen}
                onClick={() => setMobileOpen((prev) => !prev)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-2xl border border-black/10 bg-white text-black/75 transition hover:bg-black/[0.03]"
              >
                <span className="relative block h-4 w-5">
                  <span
                    className={[
                      "absolute left-0 top-0 h-0.5 w-5 rounded-full bg-current transition-all duration-300",
                      mobileOpen ? "top-[7px] rotate-45" : "",
                    ].join(" ")}
                  />
                  <span
                    className={[
                      "absolute left-0 top-[7px] h-0.5 w-5 rounded-full bg-current transition-all duration-300",
                      mobileOpen ? "opacity-0" : "opacity-100",
                    ].join(" ")}
                  />
                  <span
                    className={[
                      "absolute left-0 top-[14px] h-0.5 w-5 rounded-full bg-current transition-all duration-300",
                      mobileOpen ? "top-[7px] -rotate-45" : "",
                    ].join(" ")}
                  />
                </span>
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Mobile overlay */}
      <div
        className={[
          "fixed inset-0 z-40 bg-slate-950/30 transition-opacity duration-300 lg:hidden",
          mobileOpen
            ? "pointer-events-auto opacity-100"
            : "pointer-events-none opacity-0",
        ].join(" ")}
        onClick={() => setMobileOpen(false)}
      />

      {/* Mobile menu */}
      <div
        className={[
          "fixed inset-x-0 top-16 z-50 px-4 transition-all duration-300 lg:hidden",
          mobileOpen
            ? "pointer-events-auto translate-y-0 opacity-100"
            : "pointer-events-none -translate-y-2 opacity-0",
        ].join(" ")}
      >
        <div className="mx-auto max-w-7xl rounded-3xl border border-black/5 bg-white p-4 shadow-[0_20px_60px_rgba(15,23,42,0.16)]">
          <nav className="flex flex-col gap-2">
            {navItems.map((item) => (
              <NavItem
                key={item.to}
                to={item.to}
                label={item.label}
                onClick={() => setMobileOpen(false)}
              />
            ))}
          </nav>

          <div className="mt-4 grid gap-3 border-t border-black/5 pt-4 sm:grid-cols-2">
            <button
              onClick={() => {
                setMobileOpen(false);
                navigate("/contact");
              }}
              className="rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm font-semibold text-black/75 transition hover:text-[var(--navy)]"
            >
              Talk to Us
            </button>

            <div onClick={() => setMobileOpen(false)}>
              <Button3D onClick={() => navigate("/packages")}>
                Get Connected
              </Button3D>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}