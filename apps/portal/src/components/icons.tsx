// Ícones de interface do Design System ODBr (SVG inline, cor por currentColor).
// GitHub: ícone "github" do Bootstrap Icons 1.11.3 (licença MIT,
// https://icons.getbootstrap.com/icons/github/). Cópia em design-system/assets/icons.

interface IconProps {
  size?: number;
}

const GITHUB =
  "M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8";

export function GithubIcon({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 16 16" fill="currentColor" aria-hidden="true" focusable="false">
      <path d={GITHUB} />
    </svg>
  );
}

export function MailIcon({ size = 16 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      <path d="M4 6h16v12H4zM4 7l8 6 8-6" />
    </svg>
  );
}

/** Informação (círculo com "i", contorno): abre a explicação de um bloco (DS 2.3.11). */
export function InfoIcon({ size = 18 }: IconProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true" focusable="false">
      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
      <path d="M12 11v6" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" />
      <circle cx="12" cy="7.5" r="1.4" fill="currentColor" />
    </svg>
  );
}

// Ícones da página Apoie (traço próprio, 24 × 24, sem logos de marca).
function Stroke({ size = 20, children }: IconProps & { children: React.ReactNode }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {children}
    </svg>
  );
}

export const HeartIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M12 20s-7-4.4-9.2-8.6C1.3 8.4 3 4.5 6.6 4.5c2.1 0 3.5 1.2 4.4 2.6.9-1.4 2.3-2.6 4.4-2.6 3.6 0 5.3 3.9 3.8 6.9C19 15.6 12 20 12 20Z" />
  </Stroke>
);
export const CupIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M4 8h13v5a6 6 0 0 1-6 6h-1a6 6 0 0 1-6-6V8Z" />
    <path d="M17 10h1.5a2.5 2.5 0 0 1 0 5H17" />
    <path d="M8 2.5v2.5M12 2.5v2.5" />
  </Stroke>
);
export const CodeIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M8 7l-5 5 5 5M16 7l5 5-5 5" />
  </Stroke>
);
export const QrIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="3" y="3" width="7" height="7" rx="1" />
    <rect x="14" y="3" width="7" height="7" rx="1" />
    <rect x="3" y="14" width="7" height="7" rx="1" />
    <path d="M14 14h3v3M21 14v.01M17 21h4v-4M14 18v3" />
  </Stroke>
);
export const ShareIcon = (p: IconProps) => (
  <Stroke {...p}>
    <circle cx="18" cy="5" r="3" />
    <circle cx="6" cy="12" r="3" />
    <circle cx="18" cy="19" r="3" />
    <path d="M8.6 13.5l6.8 4M15.4 6.5l-6.8 4" />
  </Stroke>
);
export const BugIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="7" y="7" width="10" height="13" rx="5" />
    <path d="M9 4l1.5 2M15 4l-1.5 2M3 12h4M17 12h4M4 7l3 2M20 7l-3 2M4 18l3-2M20 18l-3-2" />
  </Stroke>
);
export const DatabaseIcon = (p: IconProps) => (
  <Stroke {...p}>
    <ellipse cx="12" cy="5" rx="8" ry="3" />
    <path d="M4 5v14c0 1.7 3.6 3 8 3s8-1.3 8-3V5M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3" />
  </Stroke>
);

// Ícones da versão mobile (B3): menu, fechar, filtros e lista de indicadores.
export const MenuIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M4 7h16M4 12h16M4 17h16" />
  </Stroke>
);
export const CloseIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M6 6l12 12M18 6L6 18" />
  </Stroke>
);
export const FilterIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M4 6h16M7 12h10M10 18h4" />
  </Stroke>
);
export const ListIcon = (p: IconProps) => (
  <Stroke {...p}>
    <path d="M9 6h11M9 12h11M9 18h11M4.5 6h.01M4.5 12h.01M4.5 18h.01" />
  </Stroke>
);

// Cabeçalho e rodapé (DS 2.9): Instagram em traço próprio (quadrado arredondado, lente e
// ponto, sem o logotipo colorido da marca) e globo do seletor de idioma.
export const InstagramIcon = (p: IconProps) => (
  <Stroke {...p}>
    <rect x="3" y="3" width="18" height="18" rx="5" />
    <circle cx="12" cy="12" r="4" />
    <path d="M17.5 6.5h.01" />
  </Stroke>
);
export const GlobeIcon = (p: IconProps) => (
  <Stroke {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M3 12h18M12 3c2.5 2.6 3.8 5.6 3.8 9s-1.3 6.4-3.8 9c-2.5-2.6-3.8-5.6-3.8-9S9.5 5.6 12 3Z" />
  </Stroke>
);
