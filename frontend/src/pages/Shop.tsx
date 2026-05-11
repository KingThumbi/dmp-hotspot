import { useMemo, useState } from "react";
import Button3D from "../components/ui/Button3D";

const WHATSAPP_NUMBER = "254780912362";

const categories = [
  "Routers",
  "MikroTik",
  "Switches",
  "Access Points",
  "Fibre Optic",
  "Ethernet Cables",
  "Cabinets/Racks",
  "CCTV/IP Cameras",
  "UPS/Power Backup",
  "Hotspot Accessories",
] as const;

type Category = (typeof categories)[number];
type Availability = "In stock" | "Limited stock" | "Pre-order" | "Request Quote";

type Product = {
  id: number;
  category: Category;
  brand: string;
  model: string;
  specs: string[];
  availability: Availability;
  priceKes?: number;
  badge?: string;
  image: string;
  imageAlt: string;
  useCase: string;
};

type Bundle = {
  name: string;
  audience: string;
  items: string[];
  price: string;
};

const products: Product[] = [
  {
    id: 1,
    category: "Routers",
    brand: "TP-Link",
    model: "Archer AX23 Wi-Fi 6 Router",
    specs: ["AX1800 dual-band", "Gigabit WAN/LAN", "OFDMA + MU-MIMO"],
    availability: "In stock",
    priceKes: 9500,
    badge: "Home upgrade",
    image: "https://images.unsplash.com/photo-1606904825846-647eb07f5be2?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Modern wireless router on a clean desk",
    useCase: "Fast home and small-office Wi-Fi with modern device support.",
  },
  {
    id: 2,
    category: "MikroTik",
    brand: "MikroTik",
    model: "hEX S RB760iGS",
    specs: ["5x Gigabit ports", "SFP cage", "RouterOS L4"],
    availability: "Limited stock",
    priceKes: 11800,
    badge: "ISP favorite",
    image: "https://images.unsplash.com/photo-1558494949-ef010cbdcc31?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Network equipment and patch cables in a server rack",
    useCase: "Reliable gateway routing for managed sites and ISP edge installs.",
  },
  {
    id: 3,
    category: "Switches",
    brand: "Mercusys",
    model: "MS108G 8-Port Gigabit Switch",
    specs: ["8x 10/100/1000 Mbps", "Fanless metal body", "Plug and play"],
    availability: "In stock",
    priceKes: 3400,
    image: "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Ethernet switches and network cables",
    useCase: "Simple wired expansion for homes, offices, and camera networks.",
  },
  {
    id: 4,
    category: "Access Points",
    brand: "Ubiquiti",
    model: "UniFi U6+ Access Point",
    specs: ["Wi-Fi 6", "PoE powered", "Ceiling mount kit"],
    availability: "Request Quote",
    badge: "Premium Wi-Fi",
    image: "https://images.unsplash.com/photo-1600267165477-6d4cc741b379?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Ceiling mounted wireless access point",
    useCase: "Elegant managed Wi-Fi for offices, homes, hospitality, and venues.",
  },
  {
    id: 5,
    category: "Fibre Optic",
    brand: "Dmpolin",
    model: "FTTH Drop Cable Kit",
    specs: ["Single-mode fibre", "SC/APC connectors", "Indoor/outdoor run"],
    availability: "Pre-order",
    priceKes: 2800,
    image: "https://images.unsplash.com/photo-1634768839835-2bcd827b69ee?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Fibre optic cable strands glowing with light",
    useCase: "Clean last-mile fibre drops and customer premise preparation.",
  },
  {
    id: 6,
    category: "Ethernet Cables",
    brand: "LinkPro",
    model: "Cat6 Outdoor Cable 305m",
    specs: ["Pure copper", "UV-resistant jacket", "305m pull box"],
    availability: "In stock",
    priceKes: 18500,
    badge: "Installer grade",
    image: "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Ethernet patch cables in a network cabinet",
    useCase: "Outdoor runs, structured cabling, access points, and CCTV.",
  },
  {
    id: 7,
    category: "Cabinets/Racks",
    brand: "Netrack",
    model: "6U Wall Mount Cabinet",
    specs: ["Glass front door", "Fan ready", "Cable entry points"],
    availability: "Limited stock",
    priceKes: 12500,
    image: "https://images.unsplash.com/photo-1597852074816-d933c7d2b988?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Organized server rack with network equipment",
    useCase: "Tidy network termination for homes, offices, and small POPs.",
  },
  {
    id: 8,
    category: "CCTV/IP Cameras",
    brand: "Hikvision",
    model: "4MP PoE Turret Camera",
    specs: ["4MP lens", "Infrared night vision", "PoE + weatherproof"],
    availability: "Request Quote",
    image: "https://images.unsplash.com/photo-1558002038-1055907df827?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Security camera mounted on an exterior wall",
    useCase: "Clear perimeter and business surveillance over PoE networks.",
  },
  {
    id: 9,
    category: "UPS/Power Backup",
    brand: "APC",
    model: "Easy UPS 1200VA",
    specs: ["1200VA/650W", "AVR protection", "Router + ONT backup"],
    availability: "In stock",
    priceKes: 16500,
    badge: "Power stable",
    image: "https://images.unsplash.com/photo-1621905252507-b35492cc74b4?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Power backup and electrical equipment installation",
    useCase: "Keep routers, ONTs, switches, and CCTV alive through outages.",
  },
  {
    id: 10,
    category: "Hotspot Accessories",
    brand: "Dmpolin",
    model: "Outdoor Hotspot Starter Kit",
    specs: ["Weather box", "PoE injector", "Mounting hardware"],
    availability: "Request Quote",
    badge: "For venues",
    image: "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Networking equipment prepared for deployment",
    useCase: "Fast hotspot setup for cafes, apartments, events, and kiosks.",
  },
  {
    id: 11,
    category: "MikroTik",
    brand: "MikroTik",
    model: "cAP ac Dual-Band AP",
    specs: ["2.4/5GHz Wi-Fi", "PoE in/out", "RouterOS managed"],
    availability: "In stock",
    priceKes: 10200,
    image: "https://images.unsplash.com/photo-1562408590-e32931084e23?auto=format&fit=crop&w=900&q=80",
    imageAlt: "White wireless access point on a modern wall",
    useCase: "Managed indoor hotspot and office wireless coverage.",
  },
  {
    id: 12,
    category: "Switches",
    brand: "Tenda",
    model: "TEG1105P-4-63W PoE Switch",
    specs: ["4x PoE ports", "63W budget", "CCTV/AP ready"],
    availability: "Limited stock",
    priceKes: 7200,
    image: "https://images.unsplash.com/photo-1551703599-6b3e8379aa8c?auto=format&fit=crop&w=900&q=80",
    imageAlt: "Network switch with connected ethernet cables",
    useCase: "Compact PoE power for cameras, access points, and small sites.",
  },
];

const brands = ["MikroTik", "Ubiquiti", "TP-Link", "Hikvision", "APC", "Tenda", "Mercusys", "Dmpolin"];

const bundles: Bundle[] = [
  {
    name: "Home Wi-Fi Refresh",
    audience: "Apartments and family homes",
    items: ["Wi-Fi 6 router", "Cat6 patching", "UPS backup option"],
    price: "From KES 9,500",
  },
  {
    name: "Small Office Network",
    audience: "Teams, shops, clinics, salons",
    items: ["MikroTik gateway", "Gigabit switch", "Managed access point"],
    price: "Request Quote",
  },
  {
    name: "Venue Hotspot Kit",
    audience: "Cafes, lodgings, events",
    items: ["Outdoor enclosure", "PoE injector", "Hotspot AP + mounts"],
    price: "Request Quote",
  },
  {
    name: "CCTV over PoE",
    audience: "Homes and businesses",
    items: ["PoE switch", "IP cameras", "UPS and cabinet option"],
    price: "Request Quote",
  },
];

function priceLabel(product: Product) {
  return product.priceKes ? `KES ${product.priceKes.toLocaleString()}` : "Request Quote";
}

function quoteLink(items: Product[] = []) {
  const message = items.length
    ? `Hi Dmpolin Connect, I would like a quote for: ${items
        .map((item) => `${item.brand} ${item.model}`)
        .join(", ")}.`
    : "Hi Dmpolin Connect, I would like help choosing networking equipment from the online shop.";

  return `https://wa.me/${WHATSAPP_NUMBER}?text=${encodeURIComponent(message)}`;
}

function statusClass(status: Availability) {
  if (status === "In stock") return "bg-emerald-500 text-white";
  if (status === "Limited stock") return "bg-[var(--gold)] text-black";
  if (status === "Pre-order") return "bg-blue-600 text-white";
  return "bg-slate-950 text-white";
}

function ProductImage({ product, large = false }: { product: Product; large?: boolean }) {
  return (
    <div className={`relative overflow-hidden bg-slate-100 ${large ? "h-72 rounded-[1.75rem]" : "h-56 rounded-t-[1.5rem]"}`}>
      <img
        src={product.image}
        alt={product.imageAlt}
        className="h-full w-full object-cover transition duration-700 group-hover:scale-105"
        loading="lazy"
      />
      <div className="absolute inset-0 bg-gradient-to-t from-slate-950/55 via-slate-950/5 to-white/10" />
      <div className={`absolute left-4 top-4 rounded-full px-3 py-1 text-xs font-black ${statusClass(product.availability)}`}>
        {product.availability}
      </div>
      <div className="absolute bottom-4 left-4 right-4 flex items-end justify-between gap-3">
        <span className="rounded-full bg-white/92 px-3 py-1 text-xs font-black text-[var(--navy)] shadow-sm">
          {product.category}
        </span>
        {product.badge ? (
          <span className="rounded-full bg-[var(--gold)] px-3 py-1 text-xs font-black text-black shadow-sm">
            {product.badge}
          </span>
        ) : null}
      </div>
    </div>
  );
}

function ProductModal({
  product,
  inQuote,
  onClose,
  onToggleQuote,
}: {
  product: Product;
  inQuote: boolean;
  onClose: () => void;
  onToggleQuote: () => void;
}) {
  return (
    <div className="fixed inset-0 z-[80] flex items-end bg-slate-950/55 px-3 py-4 backdrop-blur-sm sm:items-center sm:px-6">
      <div className="mx-auto max-h-[92vh] w-full max-w-5xl overflow-y-auto rounded-[2rem] bg-white shadow-[0_30px_100px_rgba(0,0,0,0.35)]">
        <div className="grid gap-0 lg:grid-cols-[1fr_0.92fr]">
          <div className="p-4 sm:p-6">
            <ProductImage product={product} large />
          </div>
          <div className="p-5 sm:p-8">
            <div className="flex items-start justify-between gap-4">
              <div>
                <div className="text-sm font-black uppercase tracking-wide text-black/45">
                  {product.brand}
                </div>
                <h2 className="mt-2 text-3xl font-black text-[var(--navy)]">
                  {product.model}
                </h2>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full border border-black/10 bg-white text-xl font-black text-black/60 transition hover:bg-slate-50"
                aria-label="Close quick view"
              >
                x
              </button>
            </div>

            <div className="mt-5 text-3xl font-black text-black">{priceLabel(product)}</div>
            <p className="mt-4 text-base font-medium leading-relaxed text-black/65">
              {product.useCase}
            </p>

            <div className="mt-6 grid gap-3 sm:grid-cols-2">
              {product.specs.map((spec) => (
                <div key={spec} className="rounded-2xl border border-black/5 bg-slate-50 p-4">
                  <div className="text-xs font-black uppercase text-black/40">Spec</div>
                  <div className="mt-1 font-bold text-black">{spec}</div>
                </div>
              ))}
            </div>

            <div className="mt-7 grid gap-3 sm:grid-cols-2">
              <button
                type="button"
                onClick={onToggleQuote}
                className="rounded-xl border border-black/10 bg-white px-5 py-3 font-black text-[var(--navy)] transition hover:-translate-y-0.5 hover:border-[var(--gold)]"
              >
                {inQuote ? "Remove from Quote" : "Add to Quote"}
              </button>
              <a
                href={quoteLink([product])}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center rounded-xl bg-[var(--gold)] px-5 py-3 font-black text-black shadow-[0_8px_0_rgba(0,0,0,0.20)] transition hover:-translate-y-0.5 active:translate-y-0.5"
              >
                WhatsApp This Item
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function ShopPage() {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState<"All" | Category>("All");
  const [availability, setAvailability] = useState<"All" | Availability>("All");
  const [selectedProduct, setSelectedProduct] = useState<Product | null>(null);
  const [quoteIds, setQuoteIds] = useState<number[]>([2, 4]);

  const quoteItems = useMemo(
    () => quoteIds.map((id) => products.find((product) => product.id === id)).filter(Boolean) as Product[],
    [quoteIds]
  );

  const filteredProducts = useMemo(() => {
    const term = query.trim().toLowerCase();

    return products.filter((product) => {
      const matchesCategory = category === "All" || product.category === category;
      const matchesAvailability =
        availability === "All" || product.availability === availability;
      const searchable = [
        product.category,
        product.brand,
        product.model,
        product.availability,
        product.useCase,
        ...product.specs,
      ]
        .join(" ")
        .toLowerCase();

      return matchesCategory && matchesAvailability && (!term || searchable.includes(term));
    });
  }, [availability, category, query]);

  const featured = products.filter((product) => product.badge).slice(0, 4);
  const quoteTotal = quoteItems.reduce((sum, product) => sum + (product.priceKes || 0), 0);

  function toggleQuote(product: Product) {
    setQuoteIds((current) =>
      current.includes(product.id)
        ? current.filter((id) => id !== product.id)
        : [...current, product.id]
    );
  }

  return (
    <div className="bg-white">
      <section className="relative -mx-4 overflow-hidden bg-[var(--navy)] px-4 py-12 text-white sm:-mx-6 sm:px-6 md:py-16 lg:-mx-8 lg:px-8">
        <div className="absolute inset-0 bg-[linear-gradient(135deg,rgba(255,255,255,0.10),transparent_35%),linear-gradient(0deg,rgba(255,215,0,0.12),transparent_45%)]" />
        <div className="relative mx-auto grid max-w-7xl gap-10 lg:grid-cols-[1fr_0.92fr] lg:items-center">
          <div className="max-w-3xl">
            <div className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/10 px-4 py-2 text-sm font-bold text-white/85">
              <span className="h-2 w-2 rounded-full bg-[var(--gold)]" />
              Field-tested networking equipment for serious installs
            </div>
            <h1 className="mt-6 text-4xl font-black leading-tight md:text-6xl">
              Dmpolin Connect Shop
            </h1>
            <p className="mt-5 max-w-2xl text-lg font-medium leading-relaxed text-white/78">
              Routers, MikroTik gateways, access points, fibre accessories, racks, cameras and power backup curated for homes, businesses, hotspots and ISP deployments.
            </p>
            <div className="mt-8 flex flex-col gap-3 sm:flex-row">
              <Button3D onClick={() => document.getElementById("shop-products")?.scrollIntoView({ behavior: "smooth" })}>
                Browse Products
              </Button3D>
              <a
                href={quoteLink(quoteItems)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center justify-center rounded-xl border border-white/20 bg-white/10 px-6 py-3 font-extrabold text-white transition hover:-translate-y-1 hover:bg-white/15"
              >
                Request a Quote
              </a>
            </div>

            <div className="mt-8 grid gap-3 sm:grid-cols-3">
              {["Same-day quote support", "Installer-grade stock", "Local setup advice"].map((item) => (
                <div key={item} className="rounded-2xl border border-white/12 bg-white/10 p-4 text-sm font-bold text-white/80">
                  {item}
                </div>
              ))}
            </div>
          </div>

          <div className="relative">
            <div className="overflow-hidden rounded-[2rem] border border-white/12 bg-white p-4 text-black shadow-[0_30px_90px_rgba(0,0,0,0.32)]">
              <div className="grid gap-4 sm:grid-cols-2">
                {featured.map((product, index) => (
                  <button
                    key={product.id}
                    type="button"
                    onClick={() => setSelectedProduct(product)}
                    className={index === 0 ? "group text-left sm:col-span-2" : "group text-left"}
                  >
                    <div className={index === 0 ? "" : "overflow-hidden rounded-2xl border border-black/5 bg-slate-50 p-3"}>
                      <ProductImage product={product} />
                      <div className="mt-3 px-1">
                        <div className="text-xs font-black uppercase text-black/45">{product.brand}</div>
                        <div className="mt-1 font-black text-[var(--navy)]">{product.model}</div>
                        <div className="mt-1 text-sm font-extrabold text-black">{priceLabel(product)}</div>
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="py-10">
        <div className="grid gap-3 rounded-[2rem] border border-black/5 bg-white p-4 shadow-[0_18px_55px_rgba(15,23,42,0.08)] sm:grid-cols-2 lg:grid-cols-4">
          {[
            ["Delivery", "Pickup, rider delivery, or installation handoff"],
            ["Support", "Configuration advice before and after purchase"],
            ["Warranty", "Brand warranty guidance and stock verification"],
            ["Deployment", "Bundle planning for Wi-Fi, fibre, CCTV and hotspots"],
          ].map(([title, detail]) => (
            <div key={title} className="rounded-2xl bg-slate-50 p-4">
              <div className="font-black text-[var(--navy)]">{title}</div>
              <p className="mt-1 text-sm font-medium text-black/60">{detail}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="py-8">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-3xl font-black text-[var(--navy)]">Featured Brands</h2>
            <p className="mt-2 max-w-2xl text-black/60">
              Practical, supportable brands selected for Kenyan homes, businesses and ISP-style networks.
            </p>
          </div>
        </div>
        <div className="mt-6 grid gap-3 sm:grid-cols-2 md:grid-cols-4">
          {brands.map((brand) => (
            <div key={brand} className="rounded-2xl border border-black/5 bg-white p-5 text-center shadow-[0_14px_40px_rgba(15,23,42,0.07)] transition hover:-translate-y-1 hover:border-[var(--gold)]/60">
              <div className="text-2xl font-black text-[var(--navy)]">{brand}</div>
              <div className="mt-1 text-xs font-bold uppercase tracking-wide text-black/40">
                Available to quote
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="py-10">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-3xl font-black text-[var(--navy)]">ISP Solution Bundles</h2>
            <p className="mt-2 max-w-2xl text-black/60">
              Start from a deployment scenario and ask us to tailor equipment, quantities and installation support.
            </p>
          </div>
          <a
            href={quoteLink(quoteItems)}
            target="_blank"
            rel="noopener noreferrer"
            className="font-black text-[var(--navy)] transition hover:text-[var(--gold)]"
          >
            Request bundle pricing
          </a>
        </div>
        <div className="mt-7 grid gap-5 lg:grid-cols-4">
          {bundles.map((bundle) => (
            <article key={bundle.name} className="rounded-[1.5rem] border border-black/5 bg-slate-950 p-5 text-white shadow-[0_20px_60px_rgba(15,23,42,0.14)] transition hover:-translate-y-1">
              <div className="text-sm font-black text-[var(--gold)]">{bundle.audience}</div>
              <h3 className="mt-2 text-xl font-black">{bundle.name}</h3>
              <ul className="mt-4 space-y-2">
                {bundle.items.map((item) => (
                  <li key={item} className="flex gap-2 text-sm text-white/75">
                    <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--gold)]" />
                    {item}
                  </li>
                ))}
              </ul>
              <div className="mt-5 font-black">{bundle.price}</div>
            </article>
          ))}
        </div>
      </section>

      <section className="py-12">
        <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
          <div>
            <h2 className="text-3xl font-black text-[var(--navy)]">Shop by Category</h2>
            <p className="mt-2 max-w-2xl text-black/60">
              Browse by the job: home Wi-Fi, hotspot, CCTV, fibre drop, rack cleanup, or backup power.
            </p>
          </div>
        </div>

        <div className="mt-7 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {categories.map((item) => (
            <button
              key={item}
              type="button"
              onClick={() => setCategory(item)}
              className={[
                "min-h-28 rounded-2xl border p-4 text-left shadow-[0_16px_40px_rgba(15,23,42,0.08)] transition hover:-translate-y-1",
                category === item
                  ? "border-[var(--gold)] bg-[var(--navy)] text-white"
                  : "border-black/5 bg-white text-black hover:border-[var(--gold)]/70",
              ].join(" ")}
            >
              <div className="text-sm font-black">{item}</div>
              <div className={category === item ? "mt-2 text-xs text-white/65" : "mt-2 text-xs text-black/50"}>
                {products.filter((product) => product.category === item).length} stocked options
              </div>
            </button>
          ))}
        </div>
      </section>

      <section id="shop-products" className="py-8">
        <div className="rounded-[2rem] border border-black/5 bg-slate-50 p-4 shadow-[0_24px_70px_rgba(15,23,42,0.08)] md:p-6">
          <div className="grid gap-4 lg:grid-cols-[1fr_220px_220px]">
            <input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Search brand, model, specs, category..."
              className="min-h-12 rounded-2xl border border-black/10 bg-white px-4 font-semibold outline-none transition focus:border-[var(--gold)]"
            />
            <select
              value={category}
              onChange={(event) => setCategory(event.target.value as "All" | Category)}
              className="min-h-12 rounded-2xl border border-black/10 bg-white px-4 font-semibold outline-none transition focus:border-[var(--gold)]"
            >
              <option value="All">All categories</option>
              {categories.map((item) => (
                <option key={item} value={item}>{item}</option>
              ))}
            </select>
            <select
              value={availability}
              onChange={(event) => setAvailability(event.target.value as "All" | Availability)}
              className="min-h-12 rounded-2xl border border-black/10 bg-white px-4 font-semibold outline-none transition focus:border-[var(--gold)]"
            >
              <option value="All">All availability</option>
              <option value="In stock">In stock</option>
              <option value="Limited stock">Limited stock</option>
              <option value="Pre-order">Pre-order</option>
              <option value="Request Quote">Request Quote</option>
            </select>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button
              type="button"
              onClick={() => {
                setQuery("");
                setCategory("All");
                setAvailability("All");
              }}
              className="rounded-full border border-black/10 bg-white px-4 py-2 text-sm font-bold text-black/70 transition hover:border-[var(--gold)]"
            >
              Clear filters
            </button>
            <span className="text-sm font-semibold text-black/50">
              Showing {filteredProducts.length} of {products.length} products
            </span>
          </div>
        </div>

        <div className="mt-8 grid gap-7 xl:grid-cols-[1fr_340px]">
          <div className="grid gap-6 md:grid-cols-2">
            {filteredProducts.map((product) => {
              const inQuote = quoteIds.includes(product.id);

              return (
                <article
                  key={product.id}
                  className="group overflow-hidden rounded-[1.5rem] border border-black/5 bg-white shadow-[0_18px_55px_rgba(15,23,42,0.10)] transition duration-300 hover:-translate-y-1 hover:shadow-[0_26px_70px_rgba(15,23,42,0.14)]"
                >
                  <ProductImage product={product} />
                  <div className="p-5">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="text-xs font-black uppercase tracking-wide text-black/45">
                          {product.brand}
                        </div>
                        <h3 className="mt-1 text-xl font-black text-[var(--navy)]">
                          {product.model}
                        </h3>
                      </div>
                    </div>

                    <p className="mt-3 text-sm font-medium leading-relaxed text-black/60">
                      {product.useCase}
                    </p>

                    <div className="mt-5 text-2xl font-black text-black">
                      {priceLabel(product)}
                    </div>

                    <ul className="mt-4 space-y-2">
                      {product.specs.slice(0, 2).map((spec) => (
                        <li key={spec} className="flex gap-2 text-sm font-semibold text-black/65">
                          <span className="mt-2 h-1.5 w-1.5 shrink-0 rounded-full bg-[var(--gold)]" />
                          {spec}
                        </li>
                      ))}
                    </ul>

                    <div className="mt-5 grid gap-3 sm:grid-cols-3">
                      <button
                        type="button"
                        onClick={() => setSelectedProduct(product)}
                        className="rounded-xl border border-black/10 bg-white px-4 py-3 text-sm font-black text-[var(--navy)] transition hover:border-[var(--gold)] sm:col-span-1"
                      >
                        Quick View
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleQuote(product)}
                        className={[
                          "rounded-xl px-4 py-3 text-sm font-black shadow-[0_8px_0_rgba(0,0,0,0.16)] transition hover:-translate-y-0.5 active:translate-y-0.5 sm:col-span-2",
                          inQuote
                            ? "bg-[var(--navy)] text-white"
                            : "bg-[var(--gold)] text-black",
                        ].join(" ")}
                      >
                        {inQuote ? "Added to Quote" : "Add to Quote"}
                      </button>
                    </div>
                  </div>
                </article>
              );
            })}
          </div>

          <aside className="xl:sticky xl:top-24 xl:self-start">
            <div className="rounded-[1.75rem] border border-black/5 bg-white p-5 shadow-[0_22px_70px_rgba(15,23,42,0.12)]">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-xs font-black uppercase tracking-wide text-black/40">
                    Quote List
                  </div>
                  <h3 className="mt-1 text-2xl font-black text-[var(--navy)]">
                    {quoteItems.length} selected
                  </h3>
                </div>
                <button
                  type="button"
                  onClick={() => setQuoteIds([])}
                  className="rounded-full border border-black/10 px-3 py-1 text-xs font-bold text-black/55 transition hover:border-[var(--gold)]"
                >
                  Clear
                </button>
              </div>

              <div className="mt-5 space-y-3">
                {quoteItems.length === 0 ? (
                  <div className="rounded-2xl bg-slate-50 p-4 text-sm font-medium text-black/55">
                    Add products to build a WhatsApp quote request.
                  </div>
                ) : (
                  quoteItems.map((product) => (
                    <div key={product.id} className="flex gap-3 rounded-2xl bg-slate-50 p-3">
                      <img src={product.image} alt="" className="h-14 w-16 rounded-xl object-cover" />
                      <div className="min-w-0 flex-1">
                        <div className="truncate text-sm font-black text-black">{product.model}</div>
                        <div className="text-xs font-bold text-black/45">{priceLabel(product)}</div>
                      </div>
                      <button
                        type="button"
                        onClick={() => toggleQuote(product)}
                        className="text-sm font-black text-black/40 hover:text-red-600"
                        aria-label={`Remove ${product.model} from quote`}
                      >
                        x
                      </button>
                    </div>
                  ))
                )}
              </div>

              <div className="mt-5 rounded-2xl border border-[var(--gold)]/35 bg-[var(--gold)]/12 p-4">
                <div className="text-xs font-black uppercase text-black/45">Indicative priced items</div>
                <div className="mt-1 text-2xl font-black text-black">
                  {quoteTotal ? `KES ${quoteTotal.toLocaleString()}` : "Quote needed"}
                </div>
              </div>

              <a
                href={quoteLink(quoteItems)}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-5 inline-flex w-full items-center justify-center rounded-xl bg-[var(--gold)] px-5 py-3 font-black text-black shadow-[0_9px_0_rgba(0,0,0,0.22)] transition hover:-translate-y-0.5 active:translate-y-0.5"
              >
                WhatsApp Quote List
              </a>
            </div>
          </aside>
        </div>

        {filteredProducts.length === 0 ? (
          <div className="mt-8 rounded-3xl border border-black/5 bg-white p-8 text-center shadow-lg">
            <div className="text-xl font-black text-[var(--navy)]">No products matched</div>
            <p className="mt-2 text-black/60">Try clearing filters or ask us to source the item for you.</p>
          </div>
        ) : null}
      </section>

      <section className="py-14">
        <div className="grid overflow-hidden rounded-[2rem] bg-[var(--navy)] text-white shadow-[0_28px_80px_rgba(0,0,128,0.22)] lg:grid-cols-[0.9fr_1.1fr]">
          <div className="p-7 md:p-10">
            <h2 className="text-3xl font-black">Built for real deployments.</h2>
            <p className="mt-3 text-white/75">
              Need a complete bill of materials for a home, office, hotspot, CCTV, or fibre project? Dmpolin can help you choose compatible gear before you buy.
            </p>
            <a
              href={quoteLink(quoteItems)}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-7 inline-flex rounded-xl bg-[var(--gold)] px-6 py-3 font-black text-black shadow-[0_10px_0_rgba(0,0,0,0.25)] transition hover:-translate-y-1"
            >
              Build My Quote
            </a>
          </div>
          <div className="grid gap-4 bg-white/8 p-7 md:grid-cols-3 md:p-10">
            {[
              ["Compatibility", "Router, PoE, fibre and camera gear checked for your use case."],
              ["Support", "Local setup guidance, configuration help, and after-sale advice."],
              ["Sourcing", "Request quote items and project bundles when stock varies."],
            ].map(([title, desc]) => (
              <div key={title} className="rounded-2xl border border-white/12 bg-white/10 p-5">
                <div className="text-lg font-black text-[var(--gold)]">{title}</div>
                <p className="mt-2 text-sm leading-relaxed text-white/72">{desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {selectedProduct ? (
        <ProductModal
          product={selectedProduct}
          inQuote={quoteIds.includes(selectedProduct.id)}
          onClose={() => setSelectedProduct(null)}
          onToggleQuote={() => toggleQuote(selectedProduct)}
        />
      ) : null}
    </div>
  );
}
