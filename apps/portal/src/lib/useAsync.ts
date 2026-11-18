"use client";

import { useEffect, useState } from "react";

export interface AsyncState<T> {
  data: T | null;
  error: Error | null;
  loading: boolean;
}

interface Settled<T> {
  key: string;
  data: T | null;
  error: Error | null;
}

// Carrega dados quando as dependências mudam. O estado "carregando" é derivado da
// chave das dependências; respostas atrasadas de chaves antigas são descartadas.
export function useAsync<T>(load: (() => Promise<T>) | null, deps: readonly unknown[], retry = 0): AsyncState<T> {
  const key = JSON.stringify([...deps, retry, Boolean(load)]);
  const [settled, setSettled] = useState<Settled<T> | null>(null);
  useEffect(() => {
    if (!load) return;
    let active = true;
    load().then(
      (data) => active && setSettled({ key, data, error: null }),
      (error: unknown) =>
        active && setSettled({ key, data: null, error: error instanceof Error ? error : new Error(String(error)) }),
    );
    return () => {
      active = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  if (!load) return { data: null, error: null, loading: false };
  if (settled?.key !== key) return { data: null, error: null, loading: true };
  return { data: settled.data, error: settled.error, loading: false };
}
