"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import type { Kpi } from "@/lib/types";

function normalize(text: string): string {
  return text.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
}

// Pesquisa nos KPIs do portal (nome, descrição, tema), sem acentos e sem caixa.
export function IndicatorSearch({ kpis }: { kpis: (Kpi & { path: string })[] }) {
  const t = useTranslations("home");
  const [q, setQ] = useState("");
  const needle = normalize(q.trim());
  const found = needle
    ? kpis.filter((k) => normalize(`${k.label} ${k.name} ${k.description} ${k.path}`).includes(needle))
    : [];
  return (
    <div role="search">
      <label htmlFor="busca" style={{ fontWeight: 600 }}>
        {t("searchLabel")}
      </label>
      <input
        id="busca"
        type="search"
        value={q}
        onChange={(e) => setQ(e.target.value)}
        placeholder={t("searchPlaceholder")}
        style={{ display: "block", width: "100%", padding: 10, marginTop: 6, borderRadius: 6, border: "1px solid var(--line)" }}
      />
      {needle ? (
        <ul aria-live="polite" style={{ listStyle: "none", padding: 0 }}>
          {found.length === 0 ? <li className="muted">{t("searchEmpty")}</li> : null}
          {found.map((k) => (
            <li key={k.kpi_id} className="card" style={{ marginTop: 8 }}>
              <Link href={`/dashboard?kpi=${k.kpi_id}`}>{k.label}</Link>
              <div className="muted small">{k.path}</div>
              <div className="small">{k.description}</div>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}
