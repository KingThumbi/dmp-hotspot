import React from "react";

type Props = {
  children: React.ReactNode;
  onClick?: () => void;
  className?: string;
  type?: "button" | "submit" | "reset";
  disabled?: boolean;
};

export default function Button3D({
  children,
  onClick,
  className = "",
  type = "button",
  disabled = false,
}: Props) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={[
        "relative inline-flex items-center justify-center",
        "px-6 py-3 rounded-xl font-extrabold",
        "bg-[var(--gold)] text-black",
        "shadow-[0_10px_0_rgba(0,0,0,0.25)]",
        "transition-transform duration-150",
        "hover:-translate-y-1 hover:shadow-[0_14px_0_rgba(0,0,0,0.22)]",
        "active:translate-y-1 active:shadow-[0_6px_0_rgba(0,0,0,0.28)]",
        "focus:outline-none focus:ring-4 focus:ring-[var(--gold)]/30",
        "disabled:opacity-60 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:hover:shadow-[0_10px_0_rgba(0,0,0,0.25)] disabled:active:translate-y-0",
        className,
      ].join(" ")}
    >
      {children}
    </button>
  );
}