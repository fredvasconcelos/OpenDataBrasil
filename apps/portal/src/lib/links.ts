// Endereços externos do portal, definidos por ambiente (nada fixo no código):
//   NEXT_PUBLIC_CONTACT_URL  → página ou "mailto:" de contato
//   NEXT_PUBLIC_REPO_URL      → repositório do projeto no GitHub
//   NEXT_PUBLIC_INSTAGRAM_URL → perfil do projeto no Instagram
//   NEXT_PUBLIC_APOIASE_URL   → campanha recorrente no Apoia.se
//   NEXT_PUBLIC_BMAC_URL      → página do Buy Me a Coffee
//   NEXT_PUBLIC_BMAC_QR       → QR Code do Buy Me a Coffee (arquivo em public/)
//   NEXT_PUBLIC_PIX_KEY       → chave PIX do projeto (texto, não URL)
//   NEXT_PUBLIC_PIX_CODE      → código PIX "copia e cola" (BR Code do QR)
//   NEXT_PUBLIC_PIX_QR        → QR Code PIX (arquivo em public/)
//   NEXT_PUBLIC_BANK_*        → dados públicos da transferência bancária
// Sem valor, o botão, o QR ou o cartão correspondente não aparece.

const clean = (value: string | undefined) => (value && value.trim() ? value.trim() : null);

export const CONTACT_URL = clean(process.env.NEXT_PUBLIC_CONTACT_URL);
export const REPO_URL = clean(process.env.NEXT_PUBLIC_REPO_URL);
export const INSTAGRAM_URL = clean(process.env.NEXT_PUBLIC_INSTAGRAM_URL);

/** Formas de doação da página /apoie. Cada uma só aparece quando configurada. */
export interface SupportLinks {
  apoiase: string | null;
  coffee: string | null;
  pix: string | null;
  /** Opcionais: QR Codes (caminhos em public/) e o PIX "copia e cola". */
  coffeeQr?: string | null;
  pixCode?: string | null;
  pixQr?: string | null;
  transfer?: BankTransfer | null;
}

/** Dados exibidos como texto para preservar zeros e dígitos verificadores. */
export interface BankTransfer {
  bank: string;
  recipient: string;
  branch: string;
  operation: string | null;
  account: string;
}

const bank = clean(process.env.NEXT_PUBLIC_BANK_NAME);
const recipient = clean(process.env.NEXT_PUBLIC_BANK_RECIPIENT);
const branch = clean(process.env.NEXT_PUBLIC_BANK_BRANCH);
const account = clean(process.env.NEXT_PUBLIC_BANK_ACCOUNT);

export const SUPPORT_LINKS: SupportLinks = {
  apoiase: clean(process.env.NEXT_PUBLIC_APOIASE_URL),
  coffee: clean(process.env.NEXT_PUBLIC_BMAC_URL),
  pix: clean(process.env.NEXT_PUBLIC_PIX_KEY),
  coffeeQr: clean(process.env.NEXT_PUBLIC_BMAC_QR),
  pixCode: clean(process.env.NEXT_PUBLIC_PIX_CODE),
  pixQr: clean(process.env.NEXT_PUBLIC_PIX_QR),
  transfer: bank && recipient && branch && account ? {
    bank, recipient, branch, account,
    operation: clean(process.env.NEXT_PUBLIC_BANK_OPERATION),
  } : null,
};

/** Links externos (http/https) abrem em nova aba; "mailto:" e rotas internas não. */
export const isExternal = (href: string) => /^https?:\/\//i.test(href);
