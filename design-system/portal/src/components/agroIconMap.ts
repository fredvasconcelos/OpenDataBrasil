// Que ícone de agropecuária cada categoria ou KPI usa (DS 2.3.14). Grupos de lavoura:
// configs/catalog/grupos/lavouras.toml (5457); produtos do LSPA (6588, c48) pelo mesmo
// critério dos grupos.

const LSPA: Record<string, string> = {
  "39428": "graos",
  "39447": "frutas",
  "39448": "hortalicas",
  "39449": "frutas",
  "39450": "raizes",
  "39451": "raizes",
  "39452": "raizes",
  "39453": "estimulantes",
  "40527": "estimulantes",
  "39454": "estimulantes",
  "39455": "estimulantes",
  "39456": "cana",
  "39457": "frutas",
  "39458": "hortalicas",
  "39459": "frutas",
  "39460": "fumo",
  "39461": "estimulantes",
  "39462": "fibras",
  "39463": "frutas",
  "39464": "frutas",
  "39465": "fibras",
  "39467": "raizes",
  "39468": "outras",
  "39469": "fibras",
  "39470": "hortalicas",
  "39471": "frutas",
};

const KPIS: Record<string, string> = {
  efetivo_rebanhos: "bovino",
  efetivo_bubalinos: "bubalino",
  efetivo_equinos: "equino",
  efetivo_suinos: "suino",
  efetivo_caprinos: "caprino",
  efetivo_ovinos: "ovino",
  efetivo_galinaceos: "galinaceo",
  efetivo_codornas: "codorna",
  abate_bovinos: "bovino",
  vacas_ordenhadas: "bovino",
  ovinos_tosquiados: "ovino",
  producao_origem_animal: "leite",
  leite_adquirido: "leite",
  producao_ovos_galinha: "ovos",
  producao_ovos_codorna: "ovos",
  ovos_produzidos: "ovos",
  producao_mel: "mel",
  producao_casulos: "casulos",
  producao_la: "la",
  producao_lavouras: "graos",
  safra_estimada: "graos",
};

/** Ícone de uma categoria ("c782:g_frutas", "c48:39463"), ou null. */
export function categoryIcon(key: string | null | undefined): string | null {
  if (!key) return null;
  const [cid, code] = key.split(":");
  if (cid === "c782" && code?.startsWith("g_")) return code.slice(2);
  if (cid === "c48" && code) return LSPA[code] ?? null;
  return null;
}

/** Ícone de um KPI (rebanhos, produtos de origem animal, lavouras), ou null. */
export function kpiIcon(kpiId: string | null | undefined): string | null {
  return kpiId ? (KPIS[kpiId] ?? null) : null;
}
