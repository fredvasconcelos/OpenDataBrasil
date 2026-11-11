// Ícones e cores dos temas (Design System ODBr v2.3 · Início, Sobre os dados).
// Ícones: traço 2 px em viewBox 24, desenhados para o ODBr. Cores: famílias em tokens.css
// (--odbr-theme-<família>-band | icon-bg | icon | border), claro e dark.
// O tema é reconhecido pelo rótulo (sem acentos/maiúsculas). Se o catálogo tiver theme_id
// estável, acrescente-o em THEME_BY_ID; tema desconhecido usa o ícone genérico e 'ardosia'.

import type { CSSProperties } from "react";

export type ThemeFamily = "azul" | "verde" | "ocre" | "petroleo" | "roxo" | "laranja" | "magenta" | "ardosia";

export const THEME_ICONS = {
  pessoas: "M16 20v-1.5a3.5 3.5 0 0 0-3.5-3.5h-5A3.5 3.5 0 0 0 4 18.5V20M10 11a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7M20 20v-1.5a3.5 3.5 0 0 0-2.5-3.35M15 4.15a3.5 3.5 0 0 1 0 6.7",
  registro: "M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zM14 3v5h5M9 13h6M9 17h4",
  casa: "M3 11l9-7 9 7M5.5 9.5V20h13V9.5M10 20v-5.5h4V20",
  gota: "M12 3.5s6 6.4 6 10.8a6 6 0 0 1-12 0c0-4.4 6-10.8 6-10.8zM9.5 15a2.5 2.5 0 0 0 2.5 2.5",
  educacao: "M2 9l10-5 10 5-10 5zM6 11v5c0 1.5 2.7 3 6 3s6-1.5 6-3v-5M22 9v6",
  trabalho: "M3 8h18v11H3zM9 8V5h6v3M3 13h18",
  saude: "M12 20s-7.5-4.6-9-9.2C2 7.6 4.2 5 7 5c2 0 3.6 1.1 5 3 1.4-1.9 3-3 5-3 2.8 0 5 2.6 4 5.8C19.5 15.4 12 20 12 20zM12 10v5M9.5 12.5h5",
  consumo: "M3 4h2l2.4 10.5a1.5 1.5 0 0 0 1.5 1.2h8.6a1.5 1.5 0 0 0 1.5-1.1L21 8H6.2M10 20h.01M17 20h.01",
  tecnologia: "M8 3h8a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1zM11 18h2",
  seguranca: "M12 3l8 3v6c0 4.5-3.4 8.2-8 9-4.6-.8-8-4.5-8-9V6zM9 12l2 2 4-4",
  agro: "M12 21V11M12 11C12 7 9 4 4 4c0 4 3 7 8 7zM12 14c0-3.5 2.6-6 7-6 0 3.5-2.6 6-7 6z",
  industria: "M3 21V10l6 4V10l6 4V5h4l2 16zM3 21h18M7 17h2M13 17h2",
  construcao: "M3 18h18M5 18v-3a7 7 0 0 1 14 0v3M10 8V5h4v3",
  comercio: "M4 9l1.5-5h13L20 9M4 9v11h16V9M4 9a3 3 0 0 0 6 0 3 3 0 0 0 4 0 3 3 0 0 0 6 0M10 20v-5h4v5",
  servicos: "M4 17h16M12 7a7 7 0 0 1 7 7v3H5v-3a7 7 0 0 1 7-7zM12 4v3M2 20h20",
  empresas: "M4 21V4h11v17M15 9h5v12M2 21h20M8 8h3M8 12h3M8 16h3",
  precos: "M3 12V4h8l10 10-8 8zM7.5 8.5h.01",
  contas: "M3 20h18M5 16l5-5 4 3 6-7M15 7h5v5",
  ambiente: "M12 21v-5M12 3l6 8h-3l4 5H5l4-5H6z",
  gestao: "M3 9l9-5 9 5M5 10v8M9 10v8M15 10v8M19 10v8M3 20h18",
  generico: "M4 6h16M4 12h16M4 18h10",
} as const;

export type ThemeIconName = keyof typeof THEME_ICONS;

export interface ThemeVisual {
  family: ThemeFamily;
  icon: ThemeIconName;
}

const THEME_BY_LABEL: Record<string, ThemeVisual> = {
  "populacao e demografia": { family: "azul", icon: "pessoas" }, // População e demografia
  "registro civil": { family: "verde", icon: "registro" }, // Registro civil
  "domicilios e familias": { family: "ocre", icon: "casa" }, // Domicílios e famílias
  "saneamento basico": { family: "petroleo", icon: "gota" }, // Saneamento básico
  "educacao": { family: "roxo", icon: "educacao" }, // Educação
  "trabalho e rendimento": { family: "laranja", icon: "trabalho" }, // Trabalho e rendimento
  "saude": { family: "magenta", icon: "saude" }, // Saúde
  "consumo e orcamentos familiares": { family: "ocre", icon: "consumo" }, // Consumo e orçamentos familiares
  "tecnologia e comunicacao": { family: "azul", icon: "tecnologia" }, // Tecnologia e comunicação
  "seguranca e vitimizacao": { family: "ardosia", icon: "seguranca" }, // Segurança e vitimização
  "agropecuaria": { family: "verde", icon: "agro" }, // Agropecuária
  "industria": { family: "ardosia", icon: "industria" }, // Indústria
  "construcao": { family: "laranja", icon: "construcao" }, // Construção
  "comercio": { family: "roxo", icon: "comercio" }, // Comércio
  "servicos": { family: "petroleo", icon: "servicos" }, // Serviços
  "empresas e organizacoes": { family: "azul", icon: "empresas" }, // Empresas e organizações
  "precos": { family: "magenta", icon: "precos" }, // Preços
  "contas nacionais e regionais": { family: "roxo", icon: "contas" }, // Contas nacionais e regionais
  "meio ambiente": { family: "verde", icon: "ambiente" }, // Meio ambiente
  "gestao publica municipal": { family: "petroleo", icon: "gestao" }, // Gestão pública municipal
};

/** Preencha com os theme_id do catálogo quando quiser não depender do rótulo. */
export const THEME_BY_ID: Record<string, ThemeVisual> = {};

const FALLBACK: ThemeVisual = { family: "ardosia", icon: "generico" };

export function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().trim();
}

export function themeVisual(theme: { theme_id?: string; label: string }): ThemeVisual {
  return (theme.theme_id && THEME_BY_ID[theme.theme_id]) || THEME_BY_LABEL[normalize(theme.label)] || FALLBACK;
}

/** Variáveis CSS da família, para usar em style={...} no contêiner do tema. */
export function themeStyle(family: ThemeFamily): CSSProperties {
  return {
    "--theme-band": `var(--odbr-theme-${family}-band)`,
    "--theme-icon-bg": `var(--odbr-theme-${family}-icon-bg)`,
    "--theme-icon": `var(--odbr-theme-${family}-icon)`,
    "--theme-border": `var(--odbr-theme-${family}-border)`,
  } as CSSProperties;
}
