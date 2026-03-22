import { motion } from "framer-motion";

const WHATSAPP_NUMBER = "254780912362"; // 0780 912 362 (Kenya)
const WHATSAPP_TEXT =
  "Hi Dmpolin Connect, I’d like to inquire about internet packages / coverage.";

function waLink() {
  const text = encodeURIComponent(WHATSAPP_TEXT);
  return `https://wa.me/${WHATSAPP_NUMBER}?text=${text}`;
}

export default function WhatsAppFloat() {
  return (
    <div className="fixed bottom-5 right-5 z-[60] hidden sm:block">
      {/* pulse ring */}
      <span
        className="
          pointer-events-none absolute inset-0 rounded-full
          animate-[ping_2.6s_ease-in-out_infinite]
          bg-emerald-500/25
        "
      />

      {/* soft glow */}
      <span
        className="
          pointer-events-none absolute -inset-3 rounded-full
          bg-emerald-500/20 blur-2xl
          opacity-70
        "
      />

      <motion.a
        href={waLink()}
        target="_blank"
        rel="noopener noreferrer"
        aria-label="Chat on WhatsApp"
        initial={{ opacity: 0, y: 14, scale: 0.96 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.35, ease: "easeOut" }}
        whileHover={{ y: -4, scale: 1.03 }}
        whileTap={{ scale: 0.98 }}
        className="
          relative inline-flex items-center gap-3
          rounded-full px-4 py-3
          bg-emerald-500 text-white
          shadow-2xl
          border border-white/20
          backdrop-blur
          focus:outline-none focus:ring-4 focus:ring-emerald-500/30
        "
      >
        {/* icon */}
        <span
          className="
            grid place-items-center
            h-10 w-10 rounded-full
            bg-white/15
          "
        >
          <svg
            viewBox="0 0 32 32"
            width="22"
            height="22"
            fill="currentColor"
            aria-hidden="true"
          >
            <path d="M19.11 17.63c-.27-.14-1.6-.79-1.85-.88-.25-.09-.43-.14-.61.14-.18.27-.7.88-.86 1.06-.16.18-.31.2-.58.07-.27-.14-1.12-.41-2.13-1.3-.79-.7-1.32-1.56-1.47-1.83-.16-.27-.02-.41.12-.55.13-.13.27-.31.41-.46.14-.16.18-.27.27-.45.09-.18.05-.34-.02-.48-.07-.14-.61-1.47-.84-2.02-.22-.53-.45-.46-.61-.46h-.52c-.18 0-.48.07-.73.34-.25.27-.95.93-.95 2.26s.97 2.62 1.11 2.8c.14.18 1.9 2.9 4.6 4.06.64.28 1.14.45 1.53.58.65.21 1.25.18 1.72.11.52-.08 1.6-.65 1.83-1.28.23-.63.23-1.17.16-1.28-.07-.11-.25-.18-.52-.32zM16.02 3C9.39 3 4 8.22 4 14.66c0 2.54.86 4.89 2.32 6.8L5 29l7.76-1.99c1.84.99 3.95 1.56 6.26 1.56 6.63 0 12.02-5.22 12.02-11.66C31.04 8.22 22.65 3 16.02 3zm0 23.24c-2.15 0-4.13-.6-5.8-1.63l-.42-.25-4.6 1.18 1.24-4.39-.28-.44c-1.31-1.86-2.07-4.09-2.07-6.45C6.09 9.44 10.56 5.2 16.02 5.2c5.46 0 9.93 4.24 9.93 9.46 0 5.22-4.47 9.46-9.93 9.46z" />
          </svg>
        </span>

        {/* label */}
        <span className="flex flex-col leading-tight pr-1">
          <span className="text-sm font-black">WhatsApp</span>
          <span className="text-[11px] text-white/90 font-semibold">
            Chat with us
          </span>
        </span>
      </motion.a>
    </div>
  );
}
