"use client";

import { useTranslations } from "next-intl";
import { useId, useState } from "react";

import { customRangeError, MAX_CUSTOM_DAYS, PERIOD_KEYS, type PeriodRequest } from "@/lib/metrics";

interface Props {
  value: PeriodRequest;
  onChange: (value: PeriodRequest) => void;
}

// Período da página Métricas (DS 2.12): 7 dias, 30 dias, 12 meses ou Personalizado.
// É outro componente que o PeriodFilter do Painel (ADR-0026, árvore de anos e meses):
// aqui o período é operacional (dias de acesso), não a dimensão de tempo da Gold.
// "Personalizado" abre as duas datas e só aplica quando o intervalo é válido (até 366 dias).
export function MetricsPeriod({ value, onChange }: Props) {
  const t = useTranslations("metrics.period");
  const errorId = useId();
  const [custom, setCustom] = useState(value.period === "custom");
  const [from, setFrom] = useState(value.period === "custom" ? value.from : "");
  const [to, setTo] = useState(value.period === "custom" ? value.to : "");
  const [error, setError] = useState<string | null>(null);
  const active = custom ? "custom" : value.period;

  const apply = () => {
    const problem = customRangeError(from, to);
    if (problem) {
      setError(t(`errors.${problem}`, { days: String(MAX_CUSTOM_DAYS) }));
      return;
    }
    setError(null);
    onChange({ period: "custom", from, to });
  };

  return (
    <div className="metrics-period">
      <div className="segmented" role="group" aria-label={t("label")}>
        {PERIOD_KEYS.map((key) => (
          <button
            key={key}
            type="button"
            aria-pressed={active === key}
            onClick={() => {
              if (key === "custom") {
                setCustom(true);
                return;
              }
              setCustom(false);
              setError(null);
              onChange({ period: key });
            }}
          >
            {t(key)}
          </button>
        ))}
      </div>
      {custom ? (
        <div className="metrics-custom">
          <label>
            {t("from")}
            <input
              type="date"
              value={from}
              onChange={(e) => setFrom(e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
            />
          </label>
          <label>
            {t("to")}
            <input
              type="date"
              value={to}
              onChange={(e) => setTo(e.target.value)}
              aria-invalid={error ? true : undefined}
              aria-describedby={error ? errorId : undefined}
            />
          </label>
          <button type="button" className="btn-outline" onClick={apply}>
            {t("apply")}
          </button>
          {error ? (
            <p id={errorId} className="metrics-error" role="alert">
              {error}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
