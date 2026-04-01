import { Outlet } from "react-router-dom";

import Navbar from "../../components/nav/Navbar";
import Footer from "../../components/footer/Footer";
import WhatsAppFloat from "../../components/floating/WhatsAppFloat";

export default function PublicLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-white text-slate-900">
      {/* Navbar */}
      <Navbar />

      {/* Main Content */}
      <main className="flex-1 pt-16">
        <div className="mx-auto w-full max-w-7xl px-4 sm:px-6 lg:px-8">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <Footer />

      {/* Floating WhatsApp */}
      <WhatsAppFloat />
    </div>
  );
}