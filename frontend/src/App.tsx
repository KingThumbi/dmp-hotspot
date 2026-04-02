import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import PublicLayout from "./app/layout/PublicLayout";
import Home from "./app/routes/Home";
import Packages from "./app/routes/Packages";

import ScrollToTop from "./components/common/ScrollToTop";
import CoveragePreview from "./components/sections/CoveragePreview";

import ContactPage from "./pages/Contact";
import PrivacyPage from "./pages/Privacy";
import TermsPage from "./pages/Terms";
import AcceptableUsePage from "./pages/AcceptableUse";
import RefundPolicyPage from "./pages/RefundPolicy";
import ServiceLevelAgreementPage from "./pages/ServiceLevelAgreement";
import SupportPage from "./pages/Support";
import DataDeletion from "./pages/DataDeletion";

import AdminLayout from "./pages/admin/AdminLayout";
import CustomersPage from "./pages/admin/Customers";
import CustomerDetailPage from "./pages/admin/CustomerDetail";
import AdminDashboardPage from "./pages/admin/Dashboard";
import PublicLeadsPage from "./pages/admin/PublicLeads";
import RenewalRemindersPage from "./pages/admin/RenewalReminders";
import SubscriptionsPage from "./pages/admin/Subscriptions";
import TicketDetailPage from "./pages/admin/TicketDetail";
import TicketsPage from "./pages/admin/Tickets";
import TransactionDetailPage from "./pages/admin/TransactionDetail";
import TransactionsPage from "./pages/admin/Transactions";

function ComingSoonPage({ title }: { title: string }) {
  return <div className="p-6">{title} (coming soon)</div>;
}

export default function App() {
  return (
    <BrowserRouter>
      <ScrollToTop />

      <Routes>
        {/* Public routes */}
        <Route element={<PublicLayout />}>
          <Route path="/" element={<Home />} />
          <Route path="/packages" element={<Packages />} />
          <Route path="/coverage" element={<CoveragePreview />} />
          <Route path="/shop" element={<ComingSoonPage title="Shop" />} />
          <Route path="/support" element={<SupportPage />} />
          <Route path="/about" element={<ComingSoonPage title="About" />} />
          <Route path="/contact" element={<ContactPage />} />

          {/* Legal routes */}
          <Route path="/privacy" element={<PrivacyPage />} />
          <Route path="/terms" element={<TermsPage />} />
          <Route path="/acceptable-use" element={<AcceptableUsePage />} />
          <Route path="/refund-policy" element={<RefundPolicyPage />} />
          <Route
            path="/service-level-agreement"
            element={<ServiceLevelAgreementPage />}
          />
          <Route path="/data-deletion" element={<DataDeletion />} />

          {/* Legacy short SLA route */}
          <Route
            path="/sla"
            element={<Navigate to="/service-level-agreement" replace />}
          />
        </Route>

        {/* Admin routes */}
        <Route path="/admin-ui" element={<AdminLayout />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboardPage />} />
          <Route path="leads" element={<PublicLeadsPage />} />
          <Route path="tickets" element={<TicketsPage />} />
          <Route path="tickets/:id" element={<TicketDetailPage />} />
          <Route path="customers" element={<CustomersPage />} />
          <Route path="customers/:id" element={<CustomerDetailPage />} />
          <Route path="subscriptions" element={<SubscriptionsPage />} />
          <Route path="transactions" element={<TransactionsPage />} />
          <Route path="transactions/:id" element={<TransactionDetailPage />} />
          <Route path="reminders" element={<RenewalRemindersPage />} />
        </Route>

        {/* Catch-all */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}