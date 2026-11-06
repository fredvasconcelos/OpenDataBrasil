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
]);
const PASS_HEADERS = ["content-type", "content-disposition", "etag", "cache-control", "x-odb-release"];

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
  if (path[0] !== "exports") {
    return Response.json({ error: { code: "not_found", message: "rota inexistente" } }, { status: 404 });
  }
  return forward(request, path, { method: "POST", body: await request.text() });
}
