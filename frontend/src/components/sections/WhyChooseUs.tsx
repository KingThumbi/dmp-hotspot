export default function WhyChooseUs() {
  const items = [
    { title: "Stable Speeds", desc: "Consistent performance built for daily use." },
    { title: "Responsive Support", desc: "Quick help via phone and WhatsApp." },
    { title: "Secure Network", desc: "Safe infrastructure and protected access." },
    { title: "Scalable", desc: "From home users to enterprise-ready expansion." },
  ];

  return (
    <section className="py-14 bg-white">
      <div className="max-w-6xl mx-auto px-4">
        <h2 className="text-3xl font-extrabold text-[var(--navy)]">Why Dmpolin Connect</h2>
        <p className="mt-3 text-black/65 max-w-2xl">
          Built as a technology infrastructure company — not just an ISP.
        </p>

        <div className="mt-8 grid sm:grid-cols-2 lg:grid-cols-4 gap-5">
          {items.map((x) => (
            <div key={x.title} className="rounded-2xl bg-[var(--gray-light)] border border-black/5 p-6 shadow-sm">
              <div className="text-[var(--navy)] font-extrabold">{x.title}</div>
              <div className="text-sm text-black/65 mt-2">{x.desc}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
