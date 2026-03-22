import { motion } from "framer-motion";
import Button3D from "../ui/Button3D";

type Props = {
  title: string;
  priceKes: number;
  subtitle?: string;
  perks: string[];
  onSubscribe?: () => void;
  badge?: string;
};

function formatKes(n: number) {
  return `KES ${n.toLocaleString("en-KE")}`;
}

export default function PackageCard({
  title,
  priceKes,
  subtitle,
  perks,
  onSubscribe,
  badge,
}: Props) {
  return (
    <motion.div
      className="
        relative group rounded-3xl bg-white border border-black/5
        shadow-[0_18px_40px_rgba(0,0,0,0.08)]
        overflow-hidden
      "
      whileHover={{
        scale: 1.03,
        boxShadow: "0 28px 60px rgba(0,0,0,0.14)",
      }}
      transition={{ duration: 0.18, ease: "easeOut" }}
    >
      <div className="h-1 w-full bg-gradient-to-r from-[var(--gold)] via-[var(--navy)] to-[var(--gold)] opacity-80" />

      <div className="p-6 flex flex-col">
        <div className="flex items-start justify-between gap-3">
          <div>
            <div className="text-[var(--navy)] font-black text-xl">{title}</div>
            {subtitle && <div className="text-sm text-black/60 mt-1">{subtitle}</div>}
          </div>

          {badge && (
            <div className="text-xs font-black px-3 py-1 rounded-full bg-[var(--navy)] text-white">
              {badge}
            </div>
          )}
        </div>

        <div className="mt-5">
          <div className="text-4xl font-black text-black">{formatKes(priceKes)}</div>
          <div className="text-xs text-black/50 mt-1">Pay via M-Pesa • Instant processing</div>
        </div>

        <ul className="mt-5 space-y-2 text-sm text-black/75">
          {perks.map((p) => (
            <li key={p} className="flex gap-2 items-start">
              <span className="text-[var(--gold)] mt-1">●</span>
              <span>{p}</span>
            </li>
          ))}
        </ul>

        <div className="mt-6">
          <Button3D onClick={onSubscribe ?? (() => {})} className="w-full">
            Subscribe Now
          </Button3D>
        </div>
      </div>

      {/* hover glow */}
      <div className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition">
        <div className="absolute -top-20 -right-20 h-56 w-56 rounded-full bg-[var(--gold)]/18 blur-3xl" />
      </div>
    </motion.div>
  );
}
