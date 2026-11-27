// Ícones e cores dos temas (Design System ODBr v2.3 · Início, Sobre os dados).
// Ícones: Font Awesome Free 6.7.2, sólido (ADR-0039). Cores: famílias em tokens.css
// (--odbr-theme-<família>-band | icon-bg | icon | border), claro e dark.
// O tema é reconhecido pelo rótulo (sem acentos/maiúsculas). Se o catálogo tiver theme_id
// estável, acrescente-o em THEME_BY_ID; tema desconhecido usa o ícone genérico e 'ardosia'.

import type { CSSProperties } from "react";

import { FA, type FaDef } from "@/lib/faIcons";

export type ThemeFamily = "azul" | "verde" | "ocre" | "petroleo" | "roxo" | "laranja" | "magenta" | "ardosia";

// Ícones dos temas: Font Awesome Free (ADR-0039). Os nomes curtos continuam os mesmos.
export const THEME_ICONS = {
  pessoas: FA.pessoas, registro: FA.registro, casa: FA.casa, gota: FA.gota, educacao: FA.educacao,
  trabalho: FA.trabalho, saude: FA.saude, consumo: FA.consumo, tecnologia: FA.tecnologia,
  seguranca: FA.seguranca, agro: FA.agro, industria: FA.industria, construcao: FA.construcao,
  comercio: FA.comercio, servicos: FA.servicos, empresas: FA.empresas, precos: FA.precos,
  contas: FA.contasNacionais, ambiente: FA.ambiente, gestao: FA.gestao, generico: FA.generico,
} satisfies Record<string, FaDef>;

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
