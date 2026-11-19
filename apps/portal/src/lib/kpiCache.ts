// Metadados sob demanda, isolados pelo release do índice (Plano D, D1).
import { api } from "./api";
import type { Kpi } from "./types";

export class KpiCache {
  private readonly pending = new Map<string, Promise<Kpi>>();

  constructor(private readonly release: string, initial: Kpi | null) {
    if (initial) this.pending.set(initial.kpi_id, Promise.resolve(initial));
  }

  get(id: string): Promise<Kpi> {
    const existing = this.pending.get(id);
    if (existing) return existing;
    const request = api.kpi(id, this.release).catch((error: unknown) => {
      this.pending.delete(id);
      throw error;
    });
    this.pending.set(id, request);
    return request;
  }

  preload(id: string): void {
    void this.get(id).catch(() => undefined);
  }
}
