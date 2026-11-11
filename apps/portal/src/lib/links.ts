// Endereços externos do portal, definidos por ambiente (nada fixo no código):
//   NEXT_PUBLIC_CONTACT_URL  → página ou "mailto:" de contato
//   NEXT_PUBLIC_REPO_URL     → repositório do projeto no GitHub
// Sem valor, o botão correspondente não aparece no cabeçalho nem no rodapé.

const clean = (value: string | undefined) => (value && value.trim() ? value.trim() : null);

export const CONTACT_URL = clean(process.env.NEXT_PUBLIC_CONTACT_URL);
export const REPO_URL = clean(process.env.NEXT_PUBLIC_REPO_URL);

/** Links externos (http/https) abrem em nova aba; "mailto:" e rotas internas não. */
export const isExternal = (href: string) => /^https?:\/\//i.test(href);
