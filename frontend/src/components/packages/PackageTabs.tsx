import { useMemo, useState } from "react";
import PackageCard from "./PackageCard";
import { hotspotPackages, residentialPackages } from "../../data/packages";

type TabKey = "residential" | "hotspot";

export default function PackageTabs() {
  const [tab, setTab] = useState<TabKey>("residential");

  const header = useMemo(() => {
    return tab === "residential"
      ? { title: "Residential Packages", subtitle: "Fast, stable home internet built for everyday life." }
      : { title: "Hotspot Packages", subtitle: "Flexible bundles for individuals and groups." };
  }, [tab]);

  const tabBtn = (key: TabKey, label: string) => {
    const active = tab === key;
    return (
      <button
        onClick={() => setTab(key)}
        className={[
          "px-4 py-2 rounded-xl text-sm font-semibold transition",
          active
            ? "bg-[var(--gold)] text-black shadow-md"
            : "bg-white/10 text-white/90 hover:text-[var(--gold)] hover:bg-white/15",
        ].join(" ")}
      >
        {label}
      </button>
    );
  };

  return (
    <section className="px-4 py-12">
      <div className="max-w-6xl mx-auto">
        <div className="rounded-2xl border border-white/10">
          {/* top band */}
          <div className="bg-[var(--navy)] px-6 py-6 text-white">
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h2 className="text-2xl font-extrabold">{header.title}</h2>
                <p className="text-white/80 mt-1">{header.subtitle}</p>
              </div>

              <div className="flex gap-2">
                {tabBtn("residential", "Residential")}
                {tabBtn("hotspot", "Hotspot")}
              </div>
            </div>
          </div>

          {/* content */}
          <div className="bg-[var(--gray-light)] px-6 py-8">
            {tab === "residential" ? (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {residentialPackages.map((p) => (
                  <PackageCard
                    key={p.code}
                    title={`${p.speedMbps} Mbps`}
                    subtitle="Unlimited home internet"
                    priceKes={p.priceKes}
                    perks={p.perks}
                    badge={p.speedMbps >= 20 ? "Popular" : undefined}
                    onSubscribe={() => alert(`Subscribe: ${p.code}`)}
                  />
                ))}
              </div>
            ) : (
              <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">
                {hotspotPackages.map((p) => (
                  <PackageCard
                    key={p.code}
                    title={`${p.users} User${p.users > 1 ? "s" : ""} • ${p.duration}`}
                    subtitle="Hotspot bundle"
                    priceKes={p.priceKes}
                    perks={p.perks}
                    badge={p.duration === "Monthly" ? "Value" : undefined}
                    onSubscribe={() => alert(`Subscribe: ${p.code}`)}
                  />
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
