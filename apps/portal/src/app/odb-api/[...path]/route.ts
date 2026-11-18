// Proxy restrito para a API interna: o navegador nunca fala com a API nem com o
// banco diretamente. Só os prefixos e métodos da lista passam.
import { NextRequest } from "next/server";

const ALLOWED = new Set([
  "portal",
  "kpis",
  "geometries",
  "geographies",
  "indicators",
  "datasets",
  "sources",
  "release",
  "exports",
  "metrics",
]);
// x-odb-kpi e x-odb-format: o log do Caddy lê da resposta da exportação para contar downloads (ADR-0027).
const PASS_HEADERS = [
  "content-type",
  "content-disposition",
  "etag",
  "cache-control",
  "x-odb-release",
  "x-odb-kpi",
  "x-odb-format",
  "allow",
  "retry-after",
];

function target(path: string[], search: string): string | null {
  const first = path[0];
  if (!first || !ALLOWED.has(first) || path.some((p) => p === ".." || p.includes("/"))) return null;
  const internal = (process.env.ODB_API_INTERNAL_URL ?? "http://localhost:8000").replace(/\/$/, "");
  return `${internal}/api/v1/${path.map(encodeURIComponent).join("/")}${search}`;
}

async function forward(request: NextRequest, path: string[], init: RequestInit): Promise<Response> {
  const url = target(path, request.nextUrl.search);
  if (!url) {
    return Response.json({ error: { code: "not_found", message: "rota inexistente" } }, { status: 404 });
  }
  const headers = new Headers({ Accept: request.headers.get("accept") ?? "application/json" });
  const etag = request.headers.get("if-none-match");
  if (etag) headers.set("If-None-Match", etag);
  if (init.body) headers.set("Content-Type", "application/json");
  // IP do visitante anotado pelo proxy de borda (Caddy): a API limita por cliente e só
  // aceita este cabeçalho vindo da rede interna (ODB_API_TRUSTED_PROXIES).
  const forwarded = request.headers.get("x-forwarded-for");
  if (forwarded) headers.set("X-Forwarded-For", forwarded);
  const upstream = await fetch(url, { ...init, headers, cache: "no-store" });
  const out = new Headers();
  for (const name of PASS_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) out.set(name, value);
  }
  return new Response(upstream.status === 304 ? null : upstream.body, { status: upstream.status, headers: out });
}

export async function GET(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return forward(request, (await ctx.params).path, { method: "GET" });
}

export async function POST(request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (path[0] !== "exports") return notAllowed(path);
  return forward(request, path, { method: "POST", body: await request.text() });
}

// Métodos que o proxy não repassa: 405 com o Allow da rota (RFC 9110); rota inexistente: 404.
function notAllowed(path: string[]): Response {
  if (target(path, "") === null) {
    return Response.json({ error: { code: "not_found", message: "rota inexistente" } }, { status: 404 });
  }
  return Response.json(
    { error: { code: "method_not_allowed", message: "método não permitido" } },
    { status: 405, headers: { Allow: path[0] === "exports" ? "POST" : "GET, HEAD" } },
  );
}

async function refuse(_request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  return notAllowed((await ctx.params).path);
}

export { refuse as PUT, refuse as PATCH, refuse as DELETE };

// OPTIONS com os métodos exatos da rota (o automático do Next anunciaria todos os do arquivo).
export async function OPTIONS(_request: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const { path } = await ctx.params;
  if (target(path, "") === null) {
    return Response.json({ error: { code: "not_found", message: "rota inexistente" } }, { status: 404 });
  }
  return new Response(null, {
    status: 204,
    headers: { Allow: path[0] === "exports" ? "POST, OPTIONS" : "GET, HEAD, OPTIONS" },
  });
}
