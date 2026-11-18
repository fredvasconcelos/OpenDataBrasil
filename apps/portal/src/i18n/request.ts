// Idioma único no MVP (pt-BR). Inglês e espanhol entram como novos arquivos em messages/.
import { getRequestConfig } from "next-intl/server";

export const LOCALE = "pt-BR";

export default getRequestConfig(async () => ({
  locale: LOCALE,
  messages: (await import(`../../messages/${LOCALE}.json`)).default,
  timeZone: "America/Sao_Paulo",
}));
