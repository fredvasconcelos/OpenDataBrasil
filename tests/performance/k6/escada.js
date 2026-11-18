// Teste de capacidade em escada da Vitrine (2026-11-17), com k6. Estende vitrine.js.
// Autorizado pelo mantenedor, contra o próprio servidor doméstico, pela rede local.
//
// Perfil de visita medido num navegador real: HTML do painel, prefetches RSC dos links do
// menu, navegação/metadados, geometria, mapa por região, série do Brasil e tabela dinâmica.
// Parte dos visitantes troca para UF ou município e consulta alguns detalhes. Só usa
// combinações de nível e período que cada KPI publica. O user agent contém "bot", então o
// agregador de métricas (ADR-0027) descarta estas linhas.
//
//   docker run --rm -i --network host -v "$OUT":/out grafana/k6:2.3.0 run \
//     -e BASE=https://vitrine.example -e PERFIL=escada \
//     --out csv=/out/raw.csv.gz --summary-export=/out/resumo.json - < escada.js
//
// PERFIL: escada (10→2000 VUs), borda (25→100, curto), pesadas (rotas sem cache), rajada.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE;
if (!BASE) throw new Error("defina BASE com a URL da origem antes de executar o teste");
const PERFIL = __ENV.PERFIL || "escada";
const UA = "Mozilla/5.0 (compatible; odb-loadtest-bot/2026-11; k6)";

const RAMPA = __ENV.RAMPA || "30s";
const PLATO = __ENV.PLATO || "2m";
const degrau = (alvo) => [
  { duration: RAMPA, target: alvo },
  { duration: PLATO, target: alvo },
];
const PERFIS = {
  escada: {
    executor: "ramping-vus",
    startVUs: 0,
    // Alvos padrão, ou a lista de ALVOS="2,5,8,..." para refinar o joelho.
    stages: (__ENV.ALVOS ? __ENV.ALVOS.split(",").map(Number) : [10, 50, 100, 200, 400, 700, 1000, 1500, 2000])
      .flatMap(degrau)
      .concat([{ duration: "30s", target: 0 }]),
    gracefulRampDown: "30s",
    exec: "visita",
  },
  borda: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [25, 50, 100].flatMap(degrau).concat([{ duration: "20s", target: 0 }]),
    gracefulRampDown: "20s",
    exec: "visita",
  },
  pesadas: {
    executor: "constant-vus",
    vus: Number(__ENV.VUS || 12),
    duration: __ENV.DURACAO || "3m",
    exec: "pesadas",
  },
  rajada: {
    executor: "constant-vus",
    vus: Number(__ENV.VUS || 4),
    duration: __ENV.DURACAO || "90s",
    exec: "rajada",
  },
};

export const options = {
  scenarios: { [PERFIL]: PERFIS[PERFIL] },
  thresholds: {
    // Interrompe a escada se a falha passar de 30% (já saturado; nada mais a aprender).
    http_req_failed: [
      { threshold: "rate<0.30", abortOnFail: PERFIL === "escada", delayAbortEval: "3m" },
    ],
  },
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "p(99)", "max"],
  discardResponseBodies: true,
  userAgent: UA,
};

const P = { timeout: "30s" };
const sorteio = (lista) => lista[Math.floor(Math.random() * lista.length)];
const UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53];

function api(caminho, nome, extra = {}) {
  return http.get(`${BASE}/odb-api/${caminho}`, {
    ...P,
    headers: { "Accept-Encoding": "gzip, zstd", ...(extra.headers || {}) },
    tags: { name: nome, tipo: "api" },
  });
}
function pagina(caminho, nome) {
  return http.get(`${BASE}${caminho}`, {
    ...P,
    headers: { "Accept-Encoding": "gzip, zstd" },
    tags: { name: nome, tipo: "pagina" },
  });
}
function prefetch(caminho) {
  return http.get(`${BASE}${caminho}?_rsc=${Math.random().toString(36).slice(2, 7)}`, {
    ...P,
    headers: { Rsc: "1", "Next-Router-Prefetch": "1", "Accept-Encoding": "gzip, zstd" },
    tags: { name: "prefetch_rsc", tipo: "pagina" },
  });
}

export function setup() {
  const nav = http
    .get(`${BASE}/odb-api/portal/navigation`, { responseType: "text", timeout: "60s" })
    .json();
  const kpis = [];
  for (const tema of nav.themes)
    for (const sub of tema.subthemes)
      for (const k of sub.kpis) {
        const pb = k.periods_by_level || {};
        // setup() é serializado em JSON pelo k6: só dados simples sobrevivem. Guardamos o
        // último período publicado por nível num mapa, não numa função.
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

export function visita(dados) {
  const k = sorteio(dados.kpis);
  const nivel0 = k.mapa.includes("regiao") ? "regiao" : k.mapa[0];
  const p0 = k.ultimo[nivel0];

  // 1. HTML do painel + prefetch dos links do menu (como o Next faz).
  const r = pagina(`/dashboard?kpi=${k.id}`, "pagina_painel");
  check(r, { "painel 200": (x) => x.status === 200 });
  ["/", "/metricas", "/apoie", "/sobre"].forEach(prefetch);
  sleep(0.3 + Math.random() * 0.7);

  // 2. O painel carrega navegação, metadados, geometria, mapa, série e tabela dinâmica.
  api("portal/navigation", "navigation");
  api(`kpis/${k.id}`, "kpi");
  api(`geometries/${nivel0}`, "geometria");
  const m = api(`kpis/${k.id}/map?level=${nivel0}&period=${p0}`, "mapa");
  check(m, { "mapa 200": (x) => x.status === 200 });
  api(`kpis/${k.id}/series?geography=brasil:1`, "serie");
  api(
    `kpis/${k.id}/pivot?level=${nivel0}&rows=territorio&cols=periodo&periods=${p0}`,
    "pivot",
  );

  // 3. Parte dos visitantes troca de nível e abre detalhes.
  sleep(1 + Math.random() * 2);
  if (k.mapa.includes("uf") && Math.random() < 0.6) {
    const pu = k.ultimo["uf"];
    api(`kpis/${k.id}/map?level=uf&period=${pu}`, "mapa_uf");
    if (k.dim && k.niveis.includes("uf")) {
      for (let i = 0; i < 3; i++) {
        sleep(0.4 + Math.random());
        api(
          `kpis/${k.id}/detail?geography=uf:${sorteio(UFS)}&dimensions=${k.dim}&period=${pu}`,
          "detalhe",
        );
      }
    }
  } else if (k.mapa.includes("municipio") && Math.random() < 0.5) {
    api(`geometries/municipio`, "geometria_mun");
    api(`kpis/${k.id}/map?level=municipio&period=${k.ultimo["municipio"]}`, "mapa_mun");
  }
  sleep(2 + Math.random() * 3);
}

// Só rotas que hoje não passam pelo cache de respostas, para medir o pior caso.
export function pesadas(dados) {
  const k = sorteio(dados.kpis);
  const e = Math.random();
  if (e < 0.35) {
    api(`kpis/${k.id}/pivot?level=uf&rows=territorio&cols=periodo`, "pivot_uf_todos");
  } else if (e < 0.6) {
    api(`kpis/${k.id}/history?geography=brasil:1`, "history_br");
  } else if (e < 0.8 && k.mapa.includes("municipio")) {
    api(`kpis/${k.id}/map?level=municipio&period=${k.ultimo["municipio"]}`, "mapa_mun");
  } else {
    api(`geometries/municipio`, "geometria_mun");
  }
}

export function rajada(dados) {
  const k = sorteio(dados.kpis);
  const nivel = k.mapa.includes("regiao") ? "regiao" : k.mapa[0];
  api(`kpis/${k.id}/map?level=${nivel}&period=${k.ultimo[nivel]}`, "rajada");
}
