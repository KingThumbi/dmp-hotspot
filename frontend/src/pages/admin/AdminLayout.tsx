import { Outlet, Link, useLocation } from "react-router-dom";

function NavLink({ to, label }: { to: string; label: string }) {
  const location = useLocation();
  const active = location.pathname === to;

  return (
    <Link
      to={to}
      className={`
        px-4 py-2 rounded-xl font-bold text-sm
        transition
        ${active
          ? "bg-[var(--navy)] text-white"
          : "bg-white border border-black/10 text-black hover:bg-[var(--gray-light)]"}
      `}
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
        <div className="mb-6">
          <h1 className="text-2xl font-extrabold text-[var(--navy)]">
            Dmpolin Admin
          </h1>
        </div>

        {/* Navigation */}
        <nav className="mb-6 flex flex-wrap gap-3">
          <NavLink to="/admin-ui/dashboard" label="Dashboard" />
          <NavLink to="/admin-ui/leads" label="Leads" />
          <NavLink to="/admin-ui/tickets" label="Tickets" />
          <NavLink to="/admin-ui/customers" label="Customers" />
          <NavLink to="/admin-ui/subscriptions" label="Subscriptions" />
          <NavLink to="/admin-ui/transactions" label="Transactions" />
        </nav>

        {/* Page Content */}
        <Outlet />
      </div>
    </section>
  );
}