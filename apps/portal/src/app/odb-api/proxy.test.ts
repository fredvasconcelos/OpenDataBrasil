import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

import { GET, POST } from "./[...path]/route";

afterEach(() => vi.unstubAllGlobals());

describe("proxy das contas", () => {
  it("encaminha o dicionário versionado e recusa sua escrita", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}"));
    vi.stubGlobal("fetch", fetch);
    const params = Promise.resolve({ path: ["dictionaries", "nascidos_vivos"] });
    const response = await GET(new NextRequest("http://portal/odb-api/dictionaries/nascidos_vivos"), { params });
    expect(response.status).toBe(200);
    expect(fetch.mock.calls[0]![0]).toMatch(/\/api\/v1\/dictionaries\/nascidos_vivos$/);
    const refused = await POST(new NextRequest("http://portal/odb-api/dictionaries", { method: "POST" }), { params });
    expect(refused.status).toBe(405);
    expect(fetch).toHaveBeenCalledTimes(1);
  });
  it("preserva a proteção de indexação e o release da ficha", async () => {
    const fetch = vi.fn().mockResolvedValue(new Response("{}", { headers: { "X-Robots-Tag": "noindex, nofollow", "X-ODB-Release": "candidato" } }));
    vi.stubGlobal("fetch", fetch);
    const response = await GET(new NextRequest("http://portal/odb-api/contas/favorecidos/0123456789abcdef?periods=2025"), { params: Promise.resolve({ path: ["contas", "favorecidos", "0123456789abcdef"] }) });
    expect(response.headers.get("x-robots-tag")).toBe("noindex, nofollow");
    expect(response.headers.get("x-odb-release")).toBe("candidato");
    expect(fetch.mock.calls[0]![0]).toMatch(/\/api\/v1\/contas\/favorecidos\/0123456789abcdef\?periods=2025$/);
  });
  it("não encaminha escrita para as contas", async () => {
    const fetch = vi.fn();
    vi.stubGlobal("fetch", fetch);
    const response = await POST(new NextRequest("http://portal/odb-api/contas/ranking", { method: "POST" }), { params: Promise.resolve({ path: ["contas", "ranking"] }) });
    expect(response.status).toBe(405);
    expect(fetch).not.toHaveBeenCalled();
  });
});
