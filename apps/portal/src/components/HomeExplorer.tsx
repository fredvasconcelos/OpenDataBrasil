"use client";

import { useTranslations } from "next-intl";
import { useState } from "react";

import { BlockCards } from "@/components/BlockCards";
import { HomeCatalog } from "@/components/HomeCatalog";
import { ContasCatalog } from "@/components/contas/ContasCatalog";
import type { BlockId } from "@/lib/blocks";
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
        {block === "contas" ? <ContasCatalog /> : null}
      </section>
    </>
  );
}
