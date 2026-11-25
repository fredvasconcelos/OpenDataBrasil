import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { afterEach, expect, it } from "vitest";

import messages from "../../messages/pt-BR.json";
import type { Seasonal } from "@/lib/types";
import { SeasonalChart } from "./SeasonalChart";

afterEach(cleanup);

const fixture = (): Seasonal => ({
  kpi_id: "obitos_mensal", geography: { geography_key: "brasil:1", name: "Brasil", level_id: "brasil" },
  unit: "Pessoas", grain: "trimestre", native_grain: "trimestre", year_from: 2023, year_to: 2026,
  series: [{ key: "total", label: "Total", categories: {}, depth: 0, points: [1, 2, 3, 4].map((n) => ({
    part: `T${n}`, value: n * 1110, status: n === 1 ? "partial_sum" : "derived_sum",
    severity: n === 1 ? "warning" : null, expected: 4, present: n === 1 ? 3 : 4,
    missing: n === 1 ? ["2026T1"] : [], blocked: [], contributors: [], input_partial: [],
  })) }], notes: [], provenance: { release_id: "teste", tables: [], derived: true, truncated: false },
});
const draw = (data: Seasonal) => render(<NextIntlClientProvider locale="pt-BR" messages={messages}>
  <SeasonalChart data={data} />
</NextIntlClientProvider>);

it("mostra uma barra por trimestre e mantém amarelo fechado até o clique", () => {
  const { container } = draw(fixture());
  expect(container.querySelectorAll(".season-bar")).toHaveLength(4);
  const warning = screen.getByRole("button", { name: "Sobre o método do gráfico: dados parciais" });
  expect(warning.getAttribute("aria-expanded")).toBe("false");
  expect(warning.classList.contains("is-warning")).toBe(true);
  expect(screen.queryByText(/Cada barra soma/)).toBeNull();
  fireEvent.click(warning);
  expect(warning.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getByText(/Sem valor: T1 2026/)).toBeTruthy();
  expect(within(screen.getByRole("status")).getByText(/3 de 4 parcelas com valor/)).toBeTruthy();
  expect(screen.getByText(/Cada barra soma a mesma parte do ano entre 2023 e 2026/)).toBeTruthy();
});

it("vermelho prevalece e explica parcela bloqueada automaticamente", () => {
  const data = fixture();
  data.series[0]!.points[1] = { ...data.series[0]!.points[1]!, value: null,
    status: "blocked_accumulation", severity: "danger", blocked: ["2024T2"] };
  draw(data);
  const danger = screen.getByRole("button", { name: "Sobre o método do gráfico: dados indisponíveis" });
  expect(danger.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getByText(/Soma indisponível: há sigilo/)).toBeTruthy();
  expect(screen.getByText(/Parcelas bloqueadas: T2 2024/)).toBeTruthy();
});

it("permite consultar por teclado os valores e a cobertura sem depender do hover", () => {
  draw(fixture());
  fireEvent.click(screen.getByRole("button", { name: "Sobre o método do gráfico: dados parciais" }));
  const summary = screen.getByText("Valores e cobertura das barras");
  expect(summary.tagName).toBe("SUMMARY");
  expect(summary.parentElement?.textContent).toContain("1.110 (parcial)");
  expect(summary.parentElement?.textContent).toContain("3 de 4 parcelas com valor");
});


it("mantém o método neutro fechado e o texto fora da área do desenho", () => {
  const data = fixture();
  data.series[0]!.points.forEach((p) => { p.severity = null; p.missing = []; });
  const { container } = draw(data);
  const button = screen.getByRole("button", { name: "Sobre o método do gráfico" });
  expect(button.getAttribute("aria-expanded")).toBe("false");
  expect(button.className).toBe("info-button");
  expect(screen.queryByRole("note")).toBeNull();
  expect(container.querySelector("figcaption")).toBeNull();
  fireEvent.click(button);
  expect(screen.getByRole("note", { name: "Como ler este gráfico" })).toBeTruthy();
  expect(container.querySelector(".series-plot")?.textContent).not.toContain("Cada barra soma");
});

it("fecha a explicação com Escape devolvendo foco e ao clicar fora", () => {
  draw(fixture());
  const button = screen.getByRole("button", { name: "Sobre o método do gráfico: dados parciais" });
  fireEvent.click(button);
  fireEvent.keyDown(document, { key: "Escape" });
  expect(button.getAttribute("aria-expanded")).toBe("false");
  expect(document.activeElement).toBe(button);
  fireEvent.click(button);
  fireEvent.pointerDown(document.body);
  expect(screen.queryByRole("note")).toBeNull();
});
