"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { CupIcon, QrIcon } from "@/components/icons";
import { SUPPORT_LINKS, type SupportLinks } from "@/lib/links";

interface Props {
  links?: SupportLinks;
}

/** Logo oficial do Apoia.se (751 × 115 px), mostrado com 32 px de altura. */
const APOIASE_LOGO = { src: "/apoie/apoiase-logo.png", width: 209, height: 32 };

interface Card {
  id: string;
  href: string;
  icon: React.ReactElement | null;
  logo: { src: string; width: number; height: number } | null;
  qr: string | null;
}

/** O que foi copiado por último (chave ou "copia e cola") e o resultado. */
type Copy = { what: "key" | "code"; ok: boolean } | null;

// Formas de doação da página /apoie (Design System ODBr, "cartão de apoio"): ícone, nome,
// frase curta e ação. Cada cartão só aparece quando o endereço ou a chave está configurado
// no ambiente (lib/links.ts); sem nenhum, a seção diz que as contas estão em preparação.
// DS 2.9: QR Codes no PIX e no Buy Me a Coffee (quando configurados, em fundo branco nos
// dois temas, para a câmera ler) e o botão "Copiar PIX copia e cola" para quem doa pelo
// celular e não consegue ler o QR da própria tela. DS 2.11: o Apoia.se aparece com o logo
// oficial da plataforma (public/apoie/apoiase-logo.png) no lugar do ícone e do título; o
// nome continua no texto alternativo, que é o título do cartão para leitores de tela.
export function SupportOptions({ links = SUPPORT_LINKS }: Props) {
  const t = useTranslations("support");
  const [copy, setCopy] = useState<Copy>(null);

  const all: (Omit<Card, "href"> & { href: string | null })[] = [
    { id: "apoiase", href: links.apoiase, icon: null, logo: APOIASE_LOGO, qr: null },
    { id: "coffee", href: links.coffee, icon: <CupIcon size={22} />, logo: null, qr: links.coffeeQr ?? null },
  ];
  const cards = all.filter((c): c is Card => Boolean(c.href));

  if (!cards.length && !links.pix) {
    return <p className="empty">{t("donate.pending")}</p>;
  }

  const copyText = async (what: "key" | "code", text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopy({ what, ok: true });
    } catch {
      setCopy({ what, ok: false });
    }
  };

  return (
    <ul className="support-grid">
      {links.pix ? (
        <li className="support-card">
          <span className="support-card-icon">
            <QrIcon size={22} />
          </span>
          <h3>{t("donate.pix.name")}</h3>
          <p>{t("donate.pix.text")}</p>
          {links.pixQr ? (
            // eslint-disable-next-line @next/next/no-img-element -- QR estático em public/, sem otimização
            <img className="support-qr" src={links.pixQr} alt={t("donate.pix.qrAlt")} width={168} height={168} />
          ) : null}
          <code className="support-pix-key">{links.pix}</code>
          <button type="button" className="support-action" onClick={() => copyText("key", links.pix ?? "")}>
            {t("donate.pix.copy")}
          </button>
          {links.pixCode ? (
            <button type="button" className="support-action support-action-ghost" onClick={() => copyText("code", links.pixCode ?? "")}>
              {t("donate.pix.copyCode")}
            </button>
          ) : null}
          <p className="support-copy-status" role="status" aria-live="polite">
            {copy
              ? copy.ok
                ? t(copy.what === "key" ? "donate.pix.copied" : "donate.pix.codeCopied")
                : t("donate.pix.copyFail")
              : ""}
          </p>
        </li>
      ) : null}
      {cards.map((c) => (
        <li key={c.id} className="support-card">
          {c.logo ? (
            <h3 className="support-card-logo">
              {/* eslint-disable-next-line @next/next/no-img-element -- logo estático em public/, sem otimização */}
              <img src={c.logo.src} alt={t(`donate.${c.id}.name`)} width={c.logo.width} height={c.logo.height} />
            </h3>
          ) : (
            <>
              <span className="support-card-icon">{c.icon}</span>
              <h3>{t(`donate.${c.id}.name`)}</h3>
            </>
          )}
          <p>{t(`donate.${c.id}.text`)}</p>
          {c.qr ? (
            // eslint-disable-next-line @next/next/no-img-element -- QR estático em public/, sem otimização
            <img className="support-qr" src={c.qr} alt={t(`donate.${c.id}.qrAlt`)} width={168} height={168} />
          ) : null}
          <a className="support-action" href={c.href} target="_blank" rel="noopener noreferrer">
            {t(`donate.${c.id}.action`)}
            <span className="sr-only"> {t("newTab")}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}
