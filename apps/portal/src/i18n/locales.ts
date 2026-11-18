// Idiomas do portal (DS 2.9). Só o pt-BR tem mensagens (messages/pt-BR.json); inglês e
// espanhol aparecem no seletor como "em breve" até ganharem o próprio arquivo de
// mensagens. Ao traduzir: criar messages/<código>.json, marcar `ready` e passar a
// escolher o idioma em i18n/request.ts (cookie ou rota).

export interface PortalLocale {
  /** Código BCP 47 do idioma (igual ao nome do arquivo em messages/). */
  code: string;
  /** Sigla curta mostrada no botão. */
  short: string;
  /** Nome do idioma escrito nele mesmo ("English", não "Inglês"). */
  name: string;
  /** Mensagens prontas: só assim o idioma pode ser escolhido. */
  ready: boolean;
}

export const LOCALES: readonly PortalLocale[] = [
  { code: "pt-BR", short: "PT", name: "Português (Brasil)", ready: true },
  { code: "en", short: "EN", name: "English", ready: false },
  { code: "es", short: "ES", name: "Español", ready: false },
];
