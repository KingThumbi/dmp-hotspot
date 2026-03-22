import { Link, NavLink, useNavigate } from "react-router-dom";
import Button3D from "../ui/Button3D";

function NavItem({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        [
          "text-sm font-semibold transition",
          "text-black/70 hover:text-[var(--navy)]",
          isActive ? "text-[var(--navy)]" : "",
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );
}

export default function Navbar() {
  const navigate = useNavigate();

  return (
    <header className="fixed top-0 left-0 right-0 z-50">
      {/* White glass navbar (startup style) */}
      <div className="bg-white/80 backdrop-blur-xl border-b border-black/10">
        <div className="container h-16 flex items-center justify-between">
          {/* Brand */}
          <Link to="/" className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-xl bg-[var(--gold)] flex items-center justify-center font-black text-black shadow-md">
              D
            </div>
            <div className="leading-tight">
              <div className="text-[var(--navy)] font-black tracking-tight">
                Dmpolin Connect
              </div>
              <div className="text-xs text-black/55 font-semibold">
                Digital Infrastructure
              </div>
            </div>
          </Link>

          {/* Links */}
          <nav className="hidden md:flex items-center gap-8">
            <NavItem to="/packages" label="Packages" />
            <NavItem to="/coverage" label="Coverage" />
            <NavItem to="/shop" label="Shop" />
            <NavItem to="/support" label="Support" />
            <NavItem to="/contact" label="Contact" />
          </nav>

          {/* CTA */}
          <div className="hidden md:block">
            <Button3D onClick={() => navigate("/packages")}>
              Get Connected
            </Button3D>
          </div>

          {/* Mobile simple */}
          <div className="md:hidden">
            <button
              onClick={() => navigate("/packages")}
              className="px-4 py-2 rounded-xl font-extrabold bg-[var(--navy)] text-white shadow-md"
            >
              Packages
            </button>
          </div>
        </div>
      </div>
    </header>
  );
}
