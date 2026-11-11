import { THEME_ICONS, type ThemeIconName } from "@/lib/themes";

// Ícone de tema (traço 2 px, viewBox 24). Cor e fundo vêm do contêiner (--theme-icon, --theme-icon-bg).
export function ThemeIcon({ icon, size = 22, box = 40 }: { icon: ThemeIconName; size?: number; box?: number }) {
  return (
    <span className="theme-icon" style={{ width: box, height: box }} aria-hidden="true">
      <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d={THEME_ICONS[icon]} />
      </svg>
    </span>
  );
}
