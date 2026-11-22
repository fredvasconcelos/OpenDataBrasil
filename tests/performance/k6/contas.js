// Carga do bloco de contas públicas ao lado do painel (CP4, ADR-0034, decisão 8).
//
// Metade das visitas faz o percurso do painel (mapa, série, tabela dinâmica e detalhes de um
// KPI); a outra metade, o das contas: metadados, mapa, composição, ranking, tabela e ficha.
// Os parâmetros são sorteados (UF, página, agrupamento, ano), para medir também as consultas
// fora do cache. Aceite: p95 da tabela e do ranking das contas abaixo do p95 do painel, no
// mesmo teste, e nenhum 5xx.
//
//   docker run --rm -i --network host -v "$OUT":/out grafana/k6:2.3.0 run \
//     -e BASE=http://127.0.0.1:8010 -e PREFIXO=/api/v1 \
//     --summary-export=/out/resumo.json - < contas.js
//
// PREFIXO: /api/v1 (API direta) ou /odb-api (pelo proxy do portal, na Vitrine).
// ALVOS: usuários virtuais por degrau (padrão 10,25,50); PLATO: duração de cada degrau.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE;
if (!BASE) throw new Error("defina BASE com a URL da origem antes de executar o teste");
const PREFIXO = __ENV.PREFIXO || "/api/v1";
const UA = "Mozilla/5.0 (compatible; odb-loadtest-bot/2026-11; k6)";
const ALVOS = (__ENV.ALVOS || "10,25,50").split(",").map(Number);
const PLATO = __ENV.PLATO || "1m";

export const options = {
  scenarios: {
    misto: {
      executor: "ramping-vus",
      startVUs: 0,
      stages: ALVOS.flatMap((alvo) => [
        { duration: "20s", target: alvo },
        { duration: PLATO, target: alvo },
      ]).concat([{ duration: "15s", target: 0 }]),
      gracefulRampDown: "15s",
      exec: "visita",
    },
  },
  thresholds: {
    "http_req_failed{bloco:contas}": ["rate<0.01"],
    "http_req_failed{bloco:painel}": ["rate<0.01"],
    // Só para o resumo exportar a latência de cada bloco e rota (sempre aprovados).
    ...Object.fromEntries(
      ["contas", "painel"].map((b) => [`http_req_duration{bloco:${b}}`, ["p(95)<600000"]]),
    ),
    ...Object.fromEntries(
      [
        "painel_mapa", "painel_serie", "painel_tabela", "painel_detalhe", "contas_meta",
        "contas_mapa", "contas_composicao", "contas_serie", "contas_ranking", "contas_tabela",
        "contas_mapa_mun", "contas_ficha",
      ].map((n) => [`http_req_duration{name:${n}}`, ["p(95)<600000"]]),
    ),
  },
  summaryTrendStats: ["avg", "med", "p(90)", "p(95)", "p(99)", "max"],
  userAgent: UA,
};

const P = { timeout: "30s" };
const sorteio = (lista) => lista[Math.floor(Math.random() * lista.length)];
const UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53];
const ANOS = [2024, 2025, 2026];
const AGRUPA_A = ["territory", "function", "program", "action", "organ", "recipient_class", "recipient"];
const AGRUPA_B = ["territory", "organ", "management_unit", "recipient_class", "cnae_section", "recipient"];
const DIM_A = ["function", "transfer_type", "organ", "recipient_class", "action"];

function get(caminho, nome, bloco, texto = false) {
  const r = http.get(`${BASE}${PREFIXO}/${caminho}`, {
    ...P,
    headers: { "Accept-Encoding": "gzip" },
    responseType: texto ? "text" : "none",
    tags: { name: nome, bloco },
  });
  check(r, { [`${nome} sem 5xx`]: (x) => x.status < 500 });
  return r;
}

export function setup() {
  const nav = http
    .get(`${BASE}${PREFIXO}/portal/navigation`, { responseType: "text", timeout: "60s" })
    .json();
  const kpis = [];
  for (const tema of nav.themes)
    for (const sub of tema.subthemes)
      for (const k of sub.kpis) {
        const pb = k.periods_by_level || {};
        const ultimo = {};
        for (const n of k.map_levels || [])
          if (pb[n] && pb[n].length) ultimo[n] = pb[n][pb[n].length - 1];
        kpis.push({
          id: k.kpi_id,
          mapa: k.map_levels || [],
          niveis: k.levels || [],
          ultimo,
          dim: k.dimensions && k.dimensions.length ? k.dimensions[0].classification_id : null,
        });
      }
  return { kpis: kpis.filter((k) => k.mapa.length && Object.keys(k.ultimo).length) };
}

function painel(dados) {
  const k = sorteio(dados.kpis);
  const nivel = k.mapa.includes("uf") ? "uf" : k.mapa[0];
  const p = k.ultimo[nivel];
  get(`kpis/${k.id}`, "kpi", "painel");
  get(`kpis/${k.id}/map?level=${nivel}&period=${p}`, "painel_mapa", "painel");
  get(`kpis/${k.id}/series?geography=brasil:1`, "painel_serie", "painel");
  get(`kpis/${k.id}/pivot?level=${nivel}&rows=territorio&cols=periodo&periods=${p}`, "painel_tabela", "painel");
  sleep(0.5 + Math.random());
  if (k.dim && k.niveis.includes("uf")) {
    get(`kpis/${k.id}/detail?geography=uf:${sorteio(UFS)}&dimensions=${k.dim}&period=${p}`, "painel_detalhe", "painel");
  }
}

function contas() {
  const lente = Math.random() < 0.6 ? "A" : "B";
  const uf = `uf:${sorteio(UFS)}`;
  const ano = sorteio(ANOS);
  get("contas/meta", "contas_meta", "contas");
  get(`contas/map?lens=${lente}&level=uf&periods=${ano}`, "contas_mapa", "contas");
  if (lente === "A") {
    get(`contas/composition?lens=A&geography_key=${uf}&periods=${ano}&dimension=${sorteio(DIM_A)}`, "contas_composicao", "contas");
  }
  get(`contas/series?lens=${lente}&geography_key=${uf}&grain=mes`, "contas_serie", "contas");
  sleep(0.5 + Math.random());
  const rank = get(`contas/ranking?lens=${lente}&geography_key=${uf}&year=${ano}&page=${1 + Math.floor(Math.random() * 3)}`, "contas_ranking", "contas", true);
  const agrupa = sorteio(lente === "A" ? AGRUPA_A : AGRUPA_B);
  get(`contas/table?lens=${lente}&geography_key=${uf}&periods=${ano}&group_by=${agrupa}&page=${1 + Math.floor(Math.random() * 3)}`, "contas_tabela", "contas");
  if (Math.random() < 0.3) {
    get(`contas/map?lens=${lente}&level=municipio&within=${uf}&periods=${ano}`, "contas_mapa_mun", "contas");
  }
  if (rank.status === 200 && Math.random() < 0.5) {
    const linhas = rank.json("rows") || [];
    if (linhas.length) {
      get(`contas/favorecidos/${sorteio(linhas).recipient.recipient_id}?periods=${ano}`, "contas_ficha", "contas");
    }
  }
}

export function visita(dados) {
  if (Math.random() < 0.5) painel(dados);
  else contas();
  sleep(1 + Math.random() * 2);
}
