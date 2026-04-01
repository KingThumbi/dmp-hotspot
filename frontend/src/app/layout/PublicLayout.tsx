import { Outlet } from "react-router-dom";
import Navbar from "../../components/nav/Navbar";
import Footer from "../../components/footer/Footer";
import WhatsAppFloat from "../../components/floating/WhatsAppFloat";

export default function PublicLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-white">
      {/* Top Navigation */}
      <Navbar />

      {/* Main Page Content */}
      <main className="flex-1 pt-16">
        <div className="container-page">
          <Outlet />
        </div>
      </main>

      {/* Footer */}
      <Footer />

      {/* Floating WhatsApp Button */}
      <WhatsAppFloat />
    </div>
  );
}