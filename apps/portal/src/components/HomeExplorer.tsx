"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { useState } from "react";

import { BlockCards } from "@/components/BlockCards";
import { HomeCatalog } from "@/components/HomeCatalog";
import type { BlockId } from "@/lib/blocks";
import { normalize } from "@/lib/themes";
import type { Navigation } from "@/lib/types";

/** Abre o catálogo do bloco escolhido sem sair do Início nem misturar suas fontes. */
export function HomeExplorer({ nav, institutions }: { nav: Navigation; institutions: string[] }) {
  const t = useTranslations();
  const [block, setBlock] = useState<BlockId | null>(null);
  return (
    <>
      <BlockCards selected={block} onSelect={setBlock} />
      <section id="indicadores-do-bloco" className="block-catalog" hidden={!block} aria-labelledby="catalogo-titulo">
        {block ? <h2 id="catalogo-titulo">{t(`blocks.${block}.name`)}</h2> : null}
        {block === "estatisticas" ? <HomeCatalog nav={nav} releaseId={nav.release_id ?? null} institutions={institutions} compact /> : null}
        {block === "contas" ? <AccountsCatalog /> : null}
      </section>
    </>
  );
}

/** O catálogo oferece o painel da lente A; as demais lentes não têm painel próprio. */
function AccountsCatalog() {
  const t = useTranslations("contas");
  const [query, setQuery] = useState("");
  const found = normalize(`${t("lensName")} ${t("question")} ${t("catalog.keywords")}`).includes(normalize(query.trim()));
  return (
    <>
      <div role="search" className="accounts-search field">
        <label htmlFor="contas-busca">{t("catalog.search")}</label>
        <input id="contas-busca" type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder={t("catalog.placeholder")} />
      </div>
      {found ? <article className="card accounts-catalog-card">
        <h3>{t("lensName")}</h3>
        <p>{t("question")}</p>
        <p className="contas-hint">{t("catalog.details")}</p>
        <Link className="btn-primary" href="/contas/painel">{t("catalog.open")}</Link>
      </article> : <p role="status">{t("catalog.empty")}</p>}
    </>
  );
}
