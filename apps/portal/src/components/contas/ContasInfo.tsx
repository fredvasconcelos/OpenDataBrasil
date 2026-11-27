"use client";

// Botão i das contas: o mesmo das Estatísticas (classes info-button e chart-info do
// SeasonalChart). Notas de origem, recortes e dicas de uso ficam aqui, fora do corpo dos
// blocos. Fecha com Esc (devolvendo o foco ao botão) ou com um clique fora.
import { useEffect, useId, useRef, useState, type ReactNode } from "react";

import { InfoIcon } from "@/components/icons";

export function ContasInfo({ label, title, children, className = "chart-head" }: {
  /** Nome acessível do botão (ex.: "Sobre o mapa"). */
  label: string;
  /** Título visível ao lado do botão; quando ausente, só o botão é desenhado. */
  title?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const toggle = useRef<HTMLButtonElement>(null);
  const id = useId();
  useEffect(() => {
    if (!open) return;
    const closeOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !box.current?.contains(event.target)) setOpen(false);
    };
    const closeEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setOpen(false);
      toggle.current?.focus();
    };
    document.addEventListener("pointerdown", closeOutside);
    document.addEventListener("keydown", closeEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOutside);
      document.removeEventListener("keydown", closeEscape);
    };
  }, [open]);
  return (
    <div className={className} ref={box}>
      {title}
      <button ref={toggle} type="button" className="info-button" aria-expanded={open} aria-controls={id} aria-label={label} title={label} onClick={() => setOpen((v) => !v)}>
        <InfoIcon />
      </button>
      {open ? <div id={id} className="chart-info caption contas-info" role="note" aria-label={label}>{children}</div> : null}
    </div>
  );
}
