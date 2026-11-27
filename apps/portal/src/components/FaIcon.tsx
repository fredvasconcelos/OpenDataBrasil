import type { FaDef } from "@/lib/faIcons";

// Ícone Font Awesome (sólido, cor do contêiner). Decorativo: o texto ao lado dá o sentido.
export function FaIcon({ icon, size = 16, className }: { icon: FaDef; size?: number; className?: string }) {
  return (
    <svg className={className} width={size} height={size} viewBox={`0 0 ${icon.w} ${icon.h}`} fill="currentColor" aria-hidden="true" focusable="false" data-fa={icon.name}>
      <path d={icon.d} />
    </svg>
  );
}
