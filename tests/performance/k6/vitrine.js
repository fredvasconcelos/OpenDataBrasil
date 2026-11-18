// Teste de carga da Vitrine (plano R-V, etapa V5) com k6.
//
// Rodar contra a ORIGEM na rede local (nunca pela Cloudflare), com o limite de requisições
// da API desligado (a carga sai toda de um IP; o limite é testado à parte na V6):
//
//   docker run --rm -i -v "$PWD/out":/out grafana/k6@sha256:2dd4... run \
//     -e BASE=https://vitrine.example -e PERFIL=visita --summary-export=/out/visita.json - < vitrine.js
//
// Perfis (PERFIL):
//   visita    -> navegação típica com pausas; rampa 10 → 25 → 50 → 100 usuários simultâneos
//   municipal -> mapas municipais de KPIs e períodos aleatórios, sem pausa (consultas frias)
//   exportacao-> exportações CSV por UF, sem pausa
import http from "k6/http";
import { check, group, sleep } from "k6";

const BASE = __ENV.BASE;
if (!BASE) throw new Error("defina BASE com a URL da origem antes de executar o teste");
const PERFIL = __ENV.PERFIL || "visita";

const PERFIS = {
  visita: {
    executor: "ramping-vus",
    startVUs: 0,
    stages: [
      { duration: "1m", target: 10 },
      { duration: "2m", target: 10 },
      { duration: "1m", target: 25 },
      { duration: "2m", target: 25 },
      { duration: "1m", target: 50 },
      { duration: "2m", target: 50 },
      { duration: "1m", target: 100 },
      { duration: "2m", target: 100 },
      { duration: "30s", target: 0 },
    ],
    gracefulRampDown: "30s",
  },
  municipal: { executor: "constant-vus", vus: 10, duration: "3m" },
  exportacao: { executor: "constant-vus", vus: 4, duration: "2m" },
};

export const options = {
  scenarios: { [PERFIL]: { ...PERFIS[PERFIL], exec: PERFIL } },
  // Metas do plano: p95 < 1 s na visita típica e menos de 1% de erros.
  thresholds: {
    http_req_failed: ["rate<0.01"],
    "http_req_duration{tipo:api}": ["p(95)<1000"],
  },
  summaryTrendStats: ["avg", "min", "med", "p(90)", "p(95)", "p(99)", "max"],
  discardResponseBodies: true,
};

const UFS = [11, 12, 13, 14, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27, 28, 29, 31, 32, 33, 35, 41, 42, 43, 50, 51, 52, 53];
const sorteio = (lista) => lista[Math.floor(Math.random() * lista.length)];
const api = (caminho, nome) =>
  http.get(`${BASE}/odb-api/${caminho}`, { tags: { name: nome, tipo: "api" }, responseType: "none" });

export function setup() {
  const nav = http.get(`${BASE}/odb-api/portal/navigation`, { responseType: "text" }).json();
  const kpis = [];
  for (const tema of nav.themes)
    for (const sub of tema.subthemes)
      for (const k of sub.kpis)
        kpis.push({
          id: k.kpi_id,
          periodos: k.periods,
          mapa: k.map_levels,
          niveis: k.levels,
          dim: k.dimensions.length ? k.dimensions[0].classification_id : null,
        });
  return { kpis };
}

export function visita(dados) {
  const k = sorteio(dados.kpis);
  const periodo = k.periodos[k.periodos.length - 1];
  const nivel = k.mapa.includes("uf") ? "uf" : k.mapa[0] || "brasil";
  group("páginas", () => {
    const r = http.get(`${BASE}/`, { tags: { name: "pagina_inicio", tipo: "pagina" } });
    check(r, { "início 200": (x) => x.status === 200 });
    sleep(1 + Math.random() * 2);
    http.get(`${BASE}/dashboard?kpi=${k.id}`, { tags: { name: "pagina_painel", tipo: "pagina" } });
  });
  group("painel", () => {
    api("portal/navigation", "navigation");
    api(`kpis/${k.id}`, "kpi");
    api(`geometries/${nivel}`, "geometria");
    const m = api(`kpis/${k.id}/map?level=${nivel}&period=${periodo}`, "mapa");
    check(m, { "mapa 200": (x) => x.status === 200 });
    api(`kpis/${k.id}/series?geography=brasil:1`, "serie");
  });
  // O visitante passa o mouse por alguns estados (tooltip com detalhe).
  if (k.dim && k.niveis.includes("uf")) {
    for (let i = 0; i < 3; i++) {
      sleep(0.5 + Math.random());
      api(`kpis/${k.id}/detail?geography=uf:${sorteio(UFS)}&dimensions=${k.dim}&period=${periodo}`, "detalhe");
    }
  }
  sleep(2 + Math.random() * 3);
}

export function municipal(dados) {
  const k = sorteio(dados.kpis.filter((x) => x.mapa.includes("municipio")));
  const r = api(`kpis/${k.id}/map?level=municipio&period=${sorteio(k.periodos)}`, "mapa_municipal");
  check(r, { "mapa municipal 200": (x) => x.status === 200 });
}

export function exportacao(dados) {
  const k = sorteio(dados.kpis.filter((x) => x.niveis.includes("uf")));
  const corpo = JSON.stringify({ kpi_id: k.id, level: "uf", periods: [k.periodos[k.periodos.length - 1]], format: "csv" });
  const r = http.post(`${BASE}/odb-api/exports`, corpo, {
    headers: { "Content-Type": "application/json" },
    tags: { name: "exportacao", tipo: "api" },
  });
  check(r, { "exportação 200": (x) => x.status === 200 });
}
