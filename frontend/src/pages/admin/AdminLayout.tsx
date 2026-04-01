import { Outlet, Link, useLocation } from "react-router-dom";

function NavLink({ to, label }: { to: string; label: string }) {
  const location = useLocation();

  // Supports nested routes (e.g. /admin-ui/tickets/123)
  const active =
    location.pathname === to || location.pathname.startsWith(to + "/");

  return (
    <Link
      to={to}
      className={[
        "px-4 py-2 rounded-xl font-bold text-sm transition",
        active
          ? "bg-[var(--navy)] text-white"
          : "bg-white border border-black/10 text-black hover:bg-[var(--gray-light)]",
      ].join(" ")}
    >
      {label}
    </Link>
  );
}

export default function AdminLayout() {
  return (
    <section className="min-h-screen bg-[var(--gray-light)]">
      <div className="container-page py-6">
        {/* Header */}
        <header className="mb-6">
          <h1 className="text-2xl font-extrabold text-[var(--navy)]">
            Dmpolin Admin
          </h1>
        </header>

        {/* Navigation */}
        <nav className="mb-6 flex flex-wrap gap-3">
          <NavLink to="/admin-ui/dashboard" label="Dashboard" />
          <NavLink to="/admin-ui/leads" label="Leads" />
          <NavLink to="/admin-ui/tickets" label="Tickets" />
          <NavLink to="/admin-ui/customers" label="Customers" />
          <NavLink to="/admin-ui/subscriptions" label="Subscriptions" />
          <NavLink to="/admin-ui/transactions" label="Transactions" />
          <NavLink to="/admin-ui/reminders" label="Renewal Reminders" />
        </nav>

        {/* Page Content */}
        <main>
          <Outlet />
        </main>
      </div>
    </section>
  );
}