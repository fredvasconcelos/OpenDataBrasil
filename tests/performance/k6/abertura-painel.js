// Compara o custo do HTML de abertura do painel (Plano D, D1).
// Não substitui a escada de navegação/API nem estima visitantes reais.
// BASE aponta para uma origem de teste; os ids vêm do índice ou da navegação publicada.
import http from "k6/http";
import { check, sleep } from "k6";

const BASE = __ENV.BASE;
if (!BASE) throw new Error("defina BASE com a URL da origem de teste");

export const options = {
  vus: Number(__ENV.VUS || 70),
  duration: __ENV.DURACAO || "30s",
  gracefulStop: "10s",
  discardResponseBodies: true,
  userAgent: "odb-abertura-painel-bot/2026-11",
  summaryTrendStats: ["avg", "med", "p(95)", "p(99)", "max"],
  thresholds: { http_req_failed: ["rate<0.01"] },
};

export function setup() {
  const metadata = http.get(`${BASE}/odb-api/portal/${__ENV.INDICE || "index"}`, { responseType: "text" });
  if (metadata.status !== 200) throw new Error("o catálogo de teste não respondeu 200");
  const nav = metadata.json();
  const ids = nav.themes.flatMap((theme) => theme.subthemes.flatMap((sub) => sub.kpis.map((kpi) => kpi.kpi_id)));
  const step = Math.max(1, Math.ceil(ids.length / 20));
  const sample = ids.filter((_, i) => i % step === 0);
  if (!sample.length) throw new Error("o catálogo de teste não tem KPIs publicados");
  // A comparação mede o portal com os metadados do release já montados nas duas APIs.
  for (const id of sample) http.get(`${BASE}/dashboard?kpi=${encodeURIComponent(id)}`);
  return sample;
}

export default function (ids) {
  const id = ids[Math.floor(Math.random() * ids.length)];
  const response = http.get(`${BASE}/dashboard?kpi=${encodeURIComponent(id)}`, {
    headers: { "Accept-Encoding": "gzip" },
    tags: { name: "abertura_painel" },
    timeout: "30s",
  });
  check(response, { "painel respondeu 200": (value) => value.status === 200 });
  sleep(3 + Math.random() * 4);
}
