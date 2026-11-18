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

// Tipos de rebanho (PPM, SIDRA 3939, c79) e produtos de origem animal (SIDRA 74, c80),
// pelos códigos do descritor oficial.
const PPM: Record<string, string> = {
  "c79:2670": "bovino",
  "c79:2675": "bubalino",
  "c79:2672": "equino",
  "c79:32794": "suino",
  "c79:32795": "suino",
  "c79:2681": "caprino",
  "c79:2677": "ovino",
  "c79:32796": "galinaceo",
  "c79:32793": "galinaceo",
  "c79:2680": "codorna",
  "c80:2682": "leite",
  "c80:2685": "ovos",
  "c80:2686": "ovos",
  "c80:2687": "mel",
  "c80:2683": "casulos",
  "c80:2684": "la",
};

/** Ícone de uma categoria ("c782g:g_frutas", "c48:39463", "c79:2670"), ou null. */
export function categoryIcon(key: string | null | undefined): string | null {
  if (!key) return null;
  const [cid, code] = key.split(":");
  // Grupos de lavoura (classificação própria "c782g"; ADR-0023).
  if (cid === "c782g" && code?.startsWith("g_")) return code.slice(2);
  if (cid === "c48" && code) return LSPA[code] ?? null;
  return PPM[key] ?? null;
}
