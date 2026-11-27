import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { useAsync } from "./useAsync";

afterEach(cleanup);

it("mantém o recorte anterior durante a consulta e descarta respostas atrasadas", async () => {
  const pending = new Map<string, (value: string) => void>();
  const load = (key: string) => new Promise<string>((resolve) => pending.set(key, resolve));
  const { result, rerender } = renderHook(({ key }) => useAsync(() => load(key), [key], 0, true), { initialProps: { key: "brasil" } });
  await act(async () => pending.get("brasil")!("Brasil"));
  rerender({ key: "saude" });
  expect(result.current).toEqual({ data: "Brasil", loading: true, error: null });
  rerender({ key: "educacao" });
  await act(async () => pending.get("educacao")!("Educação"));
  await act(async () => pending.get("saude")!("Saúde"));
  expect(result.current).toEqual({ data: "Educação", loading: false, error: null });
});

it("preserva o comportamento padrão de limpar os dados quando a chave muda", async () => {
  const { result, rerender } = renderHook(({ key }) => useAsync(() => Promise.resolve(key), [key]), { initialProps: { key: "brasil" } });
  await waitFor(() => expect(result.current.data).toBe("brasil"));
  rerender({ key: "saude" });
  expect(result.current).toEqual({ data: null, loading: true, error: null });
  await waitFor(() => expect(result.current.data).toBe("saude"));
});

it("uma falha no novo recorte não apresenta os dados antigos como resposta válida", async () => {
  const error = new Error("consulta indisponível");
  const { result, rerender } = renderHook(({ fail }) => useAsync(() => fail ? Promise.reject(error) : Promise.resolve("Brasil"), [fail], 0, true), { initialProps: { fail: false } });
  await waitFor(() => expect(result.current.data).toBe("Brasil"));
  rerender({ fail: true });
  await waitFor(() => expect(result.current.error).toBe(error));
  expect(result.current.data).toBeNull();
});
