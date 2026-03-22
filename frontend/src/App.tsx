import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import PublicLayout from "./app/layout/PublicLayout";
import Home from "./app/routes/Home";
import Packages from "./app/routes/Packages";
import ContactPage from "./pages/Contact";
import CoveragePreview from "./components/sections/CoveragePreview";
import SupportPage from "./pages/Support";

import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboardPage from "./pages/admin/Dashboard";
import PublicLeadsPage from "./pages/admin/PublicLeads";
import TicketsPage from "./pages/admin/Tickets";
import CustomersPage from "./pages/admin/Customers";
import SubscriptionsPage from "./pages/admin/Subscriptions";
import TransactionsPage from "./pages/admin/Transactions";
import CustomerDetailPage from "./pages/admin/CustomerDetail";
import TicketDetailPage from "./pages/admin/TicketDetail";
import TransactionDetailPage from "./pages/admin/TransactionDetail";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/packages" element={<Packages />} />
          <Route path="/coverage" element={<CoveragePreview />} />
          <Route path="/shop" element={<div className="p-6">Shop (coming soon)</div>} />
          <Route path="/support" element={<SupportPage />} />
          <Route path="/about" element={<div className="p-6">About (coming soon)</div>} />
          <Route path="/contact" element={<ContactPage />} />
        </Route>

        {/* Admin UI */}
        <Route path="/admin-ui" element={<AdminLayout />}>
          <Route path="dashboard" element={<AdminDashboardPage />} />
          <Route path="leads" element={<PublicLeadsPage />} />
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="transactions/:id" element={<TransactionDetailPage />} />          
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}