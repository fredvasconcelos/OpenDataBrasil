"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { startTransition, useCallback, useEffect } from "react";

// Falha ao montar uma página (ex.: a API respondeu 503 porque o banco operacional
// ainda não voltou depois de um reinício do Docker). Em vez do erro cru, explica e
// tenta de novo sozinha: a indisponibilidade costuma durar segundos.
const AUTO_RETRY_MS = 15_000;

export default function PageError({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  const t = useTranslations("unavailable");
  const router = useRouter();
  // Erros de componentes do servidor: é preciso refazer a requisição, não só o render.
  const retry = useCallback(() => {
    startTransition(() => {
      router.refresh();
      reset();
    });
  }, [router, reset]);

  useEffect(() => {
    const timer = setTimeout(retry, AUTO_RETRY_MS);
    return () => clearTimeout(timer);
  }, [retry]);

  return (
    <div className="page">
      <div className="card unavailable" role="alert">
        <h1>{t("title")}</h1>
        <p>{t("lead")}</p>
        <button type="button" className="primary" onClick={retry}>
          {t("retry")}
        </button>
        {error.digest ? <p className="muted small">{t("code", { digest: error.digest })}</p> : null}
      </div>
    </div>
  );
}
