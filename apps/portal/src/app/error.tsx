"use client";

import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { startTransition, useCallback } from "react";

// Recuperação manual: não acrescenta requisições automáticas durante uma sobrecarga.
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
