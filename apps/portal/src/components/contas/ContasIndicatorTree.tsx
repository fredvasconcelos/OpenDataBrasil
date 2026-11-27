"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { FaIcon } from "@/components/FaIcon";
import { SearchGlyph } from "@/components/HomeCatalog";
import { contasGroups, loadContasCatalog, matchContas } from "@/lib/contas/catalog";
import type { ContasMeta } from "@/lib/contas/types";
import { useAsync } from "@/lib/useAsync";

const hash = () => window.location.hash;
const serverHash = () => "";
function subscribeHash(changed: () => void) {
  window.addEventListener("hashchange", changed);
  window.addEventListener("popstate", changed);
  return () => { window.removeEventListener("hashchange", changed); window.removeEventListener("popstate", changed); };
}

/** A mesma definição e busca do catálogo do Início, na árvore já usada pelo DS. */
export function ContasIndicatorTree({ meta }: { meta: ContasMeta }) {
  const t = useTranslations();
  const c = useTranslations("contas.catalog");
  const [query, setQuery] = useState("");
  const [retry, setRetry] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const search = useSearchParams();
  const currentHash = useSyncExternalStore(subscribeHash, hash, serverHash);
  const loaded = useAsync(() => loadContasCatalog(meta), [meta.release_id], retry);
  const groups = contasGroups(loaded.data, t);
  const currentLens = search.get("lens") ?? "A";
  const active = (href: string) => {
    const item = new URL(href, "https://portal.invalid");
    if ((item.searchParams.get("lens") ?? "A") !== currentLens) return false;
    if ((item.searchParams.get("area") ?? "") !== (search.get("area") ?? "")) return false;
    if ((item.searchParams.get("group") ?? "") !== (search.get("group") ?? "")) return false;
    return item.hash === currentHash || (currentLens === "C" && !currentHash && item.hash === "#fase-paid");
  };
  const listed = groups.map((group) => ({ ...group, items: group.items.filter((item) => matchContas(group, item, query)) })).filter((group) => group.items.length);
  const count = listed.reduce((sum, group) => sum + group.items.length, 0);
  useEffect(() => {
    const focus = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement;
      if (event.key !== "/" || event.ctrlKey || event.metaKey || event.altKey || target.closest("input,textarea,select,[contenteditable=true]")) return;
      event.preventDefault(); input.current?.focus();
    };
    document.addEventListener("keydown", focus);
    return () => document.removeEventListener("keydown", focus);
  }, []);
  return <nav className="themes contas-indicators" aria-label={c("indicators")}>
    <div className="tree-head"><h2>{c("indicators")}</h2><div role="search" className="tree-search"><label className="sr-only" htmlFor="contas-arvore-busca">{c("search")}</label><SearchGlyph /><input ref={input} id="contas-arvore-busca" type="search" placeholder={c("placeholder")} value={query} onChange={(event) => setQuery(event.target.value)} onKeyDown={(event) => { if (event.key === "Escape") setQuery(""); }} />{query ? null : <kbd aria-hidden="true">/</kbd>}</div><div className="tree-status" aria-live="polite">{loaded.loading ? t("contas.loading") : t("catalog.found", { count })}</div></div>
    {loaded.error ? <button className="text-btn" type="button" onClick={() => setRetry((value) => value + 1)}>{t("contas.unavailable.retry")}</button> : null}
    {listed.map((group) => <details key={`${group.id}:${Boolean(query)}:${currentLens}`} open={Boolean(query) || group.items.some((item) => active(item.href))}><summary><FaIcon icon={group.icon} size={16} /><span>{group.label}</span></summary><ul>{group.items.map((item) => <li key={item.id}><Link className="kpi-link" href={item.href} aria-current={active(item.href) ? "page" : undefined}>{item.label}</Link></li>)}</ul></details>)}
    {!loaded.loading && !listed.length ? <p className="empty">{c("empty")}</p> : null}
  </nav>;
}
