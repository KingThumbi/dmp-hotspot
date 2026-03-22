import { NavLink as RRNavLink } from "react-router-dom";

type Props = {
  to: string;
  label: string;
};

export default function NavLink({ to, label }: Props) {
  return (
    <RRNavLink
      to={to}
      className={({ isActive }) =>
        [
          "text-sm font-medium transition-colors",
          "hover:text-[var(--gold)]",
          isActive ? "text-[var(--gold)]" : "text-white/90",
        ].join(" ")
      }
    >
      {label}
    </RRNavLink>
  );
}
