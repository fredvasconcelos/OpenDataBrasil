// Gerado por infrastructure/scripts/agro_icons.py: não editar à mão (DS 2.3.14).
// Ícones de agropecuária: grupos de lavoura, rebanhos e produtos de origem animal.

export const AGRO_ICONS: Record<string, { label: string; svg: string }> = {
  graos: {
    label: "Grãos",
    svg: '<path d="M12 21V8"/><path d="M12 9c-2.2-.4-3.6-2-3.8-4.2 2.2.3 3.6 1.9 3.8 4.2zM12 9c2.2-.4 3.6-2 3.8-4.2-2.2.3-3.6 1.9-3.8 4.2z"/><path d="M12 13c-2.2-.4-3.6-2-3.8-4.2 2.2.3 3.6 1.9 3.8 4.2zM12 13c2.2-.4 3.6-2 3.8-4.2-2.2.3-3.6 1.9-3.8 4.2z"/><path d="M12 17c-2.2-.4-3.6-2-3.8-4.2 2.2.3 3.6 1.9 3.8 4.2zM12 17c2.2-.4 3.6-2 3.8-4.2-2.2.3-3.6 1.9-3.8 4.2z"/><path d="M12 5V3"/>',
  },
  frutas: {
    label: "Frutas",
    svg: '<path d="M12 8c-1.6-1.4-4.6-1.6-6.2.4C4 10.6 4.4 15 6.6 18c1.4 1.9 3 2.6 5.4 1.6 2.4 1 4 .3 5.4-1.6 2.2-3 2.6-7.4.8-9.6-1.6-2-4.6-1.8-6.2-.4z"/><path d="M12 8c0-2 .6-3.6 2-4.6"/><path d="M12.6 5.4c1.6-1.4 3.6-1.6 5-.8-1 1.6-3 2.2-5 .8z"/>',
  },
  raizes: {
    label: "Raízes e tubérculos",
    svg: '<path d="M15.5 4.5c2.6 1 3.8 3.6 2.6 6.4L10.6 20c-.9 1-2.4.9-3-.3-.6-1.2.6-3.4 1.6-5.2l3.6-6.6c.7-1.7 1.6-3.2 2.7-3.4z"/><path d="M15.5 4.5 17 2.5M17.6 6.2 20 5M13 12l2 1M11 15.5l1.8.9"/>',
  },
  hortalicas: {
    label: "Hortaliças",
    svg: '<path d="M12 20c-4.4 0-7.5-3.2-7.5-7.2C4.5 9 7 6 9.6 5.2 10.6 7.6 11.4 10 12 13c.6-3 1.4-5.4 2.4-7.8C17 6 19.5 9 19.5 12.8c0 4-3.1 7.2-7.5 7.2z"/><path d="M12 13v7M8.4 15.6 12 18M15.6 15.6 12 18"/>',
  },
  estimulantes: {
    label: "Café, cacau e estimulantes",
    svg: '<ellipse cx="12" cy="12" rx="5.6" ry="8" transform="rotate(30 12 12)"/><path d="M9.2 6.8c2.6 1.6 3.2 4.6 1.8 6.4-1.2 1.6-.8 3.4.8 4.4"/>',
  },
  cana: {
    label: "Cana-de-açúcar",
    svg: '<path d="M9 21V3M9 7.5h0M9 12h0M9 16.5h0"/><path d="M7.6 7.5h2.8M7.6 12h2.8M7.6 16.5h2.8"/><path d="M9 9.5c2.6-1.2 5.6-1.2 9.5.6-3.4 1.2-6.4 1-9.5-.6zM9 14c2.2-2.6 5-3.6 8.5-3.2-2.6 2.4-5.4 3.4-8.5 3.2z"/>',
  },
  fibras: {
    label: "Fibras",
    svg: '<path d="M8.4 12.6a3.2 3.2 0 1 1 3.6-4.4 3.2 3.2 0 1 1 3.6 4.4 3.2 3.2 0 1 1-3.6 4.4 3.2 3.2 0 1 1-3.6-4.4z"/><path d="M12 17v4M9.4 21h5.2"/>',
  },
  fumo: {
    label: "Fumo",
    svg: '<path d="M12 21c-5-3-7-7.4-6-12.4C6.6 5.8 9 3.6 12 3c3 .6 5.4 2.8 6 5.6 1 5-1 9.4-6 12.4z"/><path d="M12 21V6M12 10l-3-2M12 10l3-2M12 14l-3.6-2.4M12 14l3.6-2.4"/>',
  },
  outras: {
    label: "Outras lavouras",
    svg: '<path d="M12 21v-8"/><path d="M12 13c-.2-3.4-2.6-5.6-6.4-5.4.2 3.6 2.6 5.6 6.4 5.4zM12 11c.2-3.6 2.8-6 7-5.8-.2 3.8-2.8 6-7 5.8z"/><path d="M8 21h8"/>',
  },
  bovino: {
    label: "Bovino",
    svg: '<path d="M7 9.5c-2.4 0-4-1.2-4.5-3.5 1.6.2 3 .2 4.2-.4M17 9.5c2.4 0 4-1.2 4.5-3.5-1.6.2-3 .2-4.2-.4"/><path d="M7.2 8.4C7 12 7.6 15 8.6 17c.7 1.6 1.9 2.5 3.4 2.5s2.7-.9 3.4-2.5c1-2 1.6-5 1.4-8.6C15.4 6.8 13.8 6 12 6s-3.4.8-4.8 2.4z"/><path d="M10.2 16.6h0M13.8 16.6h0M9.6 11.2h0M14.4 11.2h0"/>',
  },
  bubalino: {
    label: "Bubalino",
    svg: '<path d="M7.4 8.2C4 8.4 2.4 6.6 3 4c1 1.6 2.6 2.2 4.6 2M16.6 8.2c3.4.2 5-1.6 4.4-4.2-1 1.6-2.6 2.2-4.6 2"/><path d="M7.2 8.4C7 12 7.6 15 8.6 17c.7 1.6 1.9 2.5 3.4 2.5s2.7-.9 3.4-2.5c1-2 1.6-5 1.4-8.6C15.4 6.8 13.8 6 12 6s-3.4.8-4.8 2.4z"/><path d="M10.2 16.6h0M13.8 16.6h0"/>',
  },
  equino: {
    label: "Equino",
    svg: '<path d="M9 21v-4.2c-2.2-1-3.4-3-3-5.6L7.4 5.6 9 3l1.4 2.2c3.4.2 6.4 2.4 7.6 6l1.2 3.4c.4 1.2-.6 2.4-1.8 2.2l-2.6-.4-1.6-2.4"/><path d="M13 21v-3.6M10.6 8.6h0"/>',
  },
  suino: {
    label: "Suíno",
    svg: '<path d="M5.4 8.6 4 4.6l4.2 1.8M18.6 8.6 20 4.6l-4.2 1.8"/><circle cx="12" cy="12.6" r="7.4"/><ellipse cx="12" cy="14.6" rx="2.8" ry="2"/><path d="M11 14.6h0M13 14.6h0M9 10.6h0M15 10.6h0"/>',
  },
  caprino: {
    label: "Caprino",
    svg: '<path d="M8.6 8C7.4 5.4 7.6 3.6 9 2.6M15.4 8c1.2-2.6 1-4.4-.4-5.4"/><path d="M8 8.2c-.4 3.6.4 7 2 9.2.6.8 1.2 1.2 2 1.2s1.4-.4 2-1.2c1.6-2.2 2.4-5.6 2-9.2-1-1-2.4-1.6-4-1.6s-3 .6-4 1.6z"/><path d="M11 18.4 12 22l1-3.6M10 11.6h0M14 11.6h0"/>',
  },
  ovino: {
    label: "Ovino",
    svg: '<path d="M6.6 16.4a3 3 0 0 1-.8-5.8 3 3 0 0 1 4.6-3.4 3 3 0 0 1 5 .2 3 3 0 0 1 3.8 4 2.8 2.8 0 0 1-1.6 5 3 3 0 0 1-5 .6 3 3 0 0 1-6 -.6z"/><path d="M8 17.4V21M15.6 17.4V21"/><path d="M3.4 9.6c-.8-1.6.2-3.2 2-3.4"/>',
  },
  galinaceo: {
    label: "Galináceo",
    svg: '<path d="M9 7.4c-.2-1.6.6-3 1.8-3.4.2-1 1.4-1.4 2-.6.8-.4 1.8.2 1.6 1.2"/><path d="M8.6 7.2C7 8 6.2 9.6 6.6 11.6L4 14.4c1.6 3.6 4.6 5.6 8.4 5.6 4.2 0 7-2.8 7.6-7.2l-2.6 1.4c-1.8.4-3.4-.6-4-2.6L13 8.4c-.6-1.4-2.6-1.8-4.4-1.2z"/><path d="M6.6 9.4 4.6 10l2 .8M10.4 21v-1.4M13.6 21v-1.2M10.6 9.2h0"/>',
  },
  codorna: {
    label: "Codorna",
    svg: '<path d="M7.6 10.4c-.4-2.6 1.4-4.6 3.8-4.6 2 0 3.6 1.4 3.8 3.4l4.8 3.4c-.8 3.8-4 6.4-8.2 6.4-3.2 0-5.4-1.8-6-4.4l1.8-4.2z"/><path d="M7.6 10.4 5.4 10.8M10.4 18.8V21M13 18.6V21M10.2 8.8h0"/><path d="M12 13c1.6.2 3 1 3.8 2.4"/>',
  },
  leite: {
    label: "Leite",
    svg: '<path d="M9.4 3h5.2v3l2 3.4V20a1 1 0 0 1-1 1H8.4a1 1 0 0 1-1-1V9.4l2-3.4z"/><path d="M9.4 6h5.2M7.4 12.4c1.6-.8 3.2-.8 4.6 0s3 .8 4.6 0"/>',
  },
  ovos: {
    label: "Ovos",
    svg: '<path d="M12 21c-3.6 0-6-2.6-6-6.4C6 9.6 8.6 3 12 3s6 6.6 6 11.6c0 3.8-2.4 6.4-6 6.4z"/>',
  },
  mel: {
    label: "Mel",
    svg: '<path d="M12 3.4 15.2 5.2v3.6L12 10.6 8.8 8.8V5.2zM8.6 9.6l3.2 1.8V15L8.6 16.8 5.4 15v-3.6zM15.4 9.6l3.2 1.8V15l-3.2 1.8-3.2-1.8v-3.6z"/><path d="M12 16.4v3.2c0 1-.8 1.6-1.6 1.6"/>',
  },
  casulos: {
    label: "Casulos do bicho-da-seda",
    svg: '<ellipse cx="12" cy="12" rx="5" ry="7.6"/><path d="M7.6 8.6c2.8 1 6 1 8.8 0M7 12c3.2 1.2 6.8 1.2 10 0M7.6 15.4c2.8 1 6 1 8.8 0"/>',
  },
  la: {
    label: "Lã",
    svg: '<circle cx="11" cy="11.4" r="6.6"/><path d="M6.4 7.6c3 .8 6.4 3.8 7.8 9.2M8.2 5.6c3.6 1.6 6.6 5 7.6 9M5 11.4c2.8.6 5.6 3 6.6 6.4"/><path d="M16.6 15c1.4 1.6 2.6 3.6 3.4 6"/>',
  },
};

export function AgroIcon({ name, size = 18 }: { name: string; size?: number }) {
  const icon = AGRO_ICONS[name];
  if (!icon) return null;
  return (
    <svg
      className="agro-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      dangerouslySetInnerHTML={{ __html: icon.svg }}
    />
  );
}
