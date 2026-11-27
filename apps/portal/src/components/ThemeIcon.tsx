import { FaIcon } from "@/components/FaIcon";
import { THEME_ICONS, type ThemeIconName } from "@/lib/themes";

// Ícone de tema (Font Awesome sólido, ADR-0039). Cor e fundo vêm do contêiner (--theme-icon, --theme-icon-bg).
export function ThemeIcon({ icon, size = 20, box = 40 }: { icon: ThemeIconName; size?: number; box?: number }) {
  return (
    <span className="theme-icon" style={{ width: box, height: box }} aria-hidden="true">
      <FaIcon icon={THEME_ICONS[icon]} size={size} />
    </span>
  );
}
