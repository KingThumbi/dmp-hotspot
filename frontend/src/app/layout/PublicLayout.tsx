import { Outlet } from "react-router-dom";
import Navbar from "../../components/nav/Navbar";
import Footer from "../../components/footer/Footer";
import WhatsAppFloat from "../../components/floating/WhatsAppFloat";

export default function PublicLayout() {
  return (
    <div className="page min-h-screen flex flex-col">
      <Navbar />

      <main className="pt-16 flex-1">
        <Outlet />
      </main>

      <Footer />
      <WhatsAppFloat />
    </div>
  );
}
