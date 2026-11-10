import type { Metadata, Viewport } from "next";
import { Nunito } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";

import { Header } from "@/components/Header";
import { THEME_STORAGE_KEY } from "@/lib/theme";

import "./globals.css";

// Fonte do Design System ODBr. Pesos 600–900; variável usada em --odbr-font.
const nunito = Nunito({
  subsets: ["latin", "latin-ext"],
  weight: ["600", "700", "800", "900"],
  display: "swap",
  variable: "--font-nunito",
});

// Aplica o tema salvo antes da primeira pintura, para a página não piscar.
const themeScript = `try{var t=localStorage.getItem("${THEME_STORAGE_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("site");
  return { title: t("name"), description: t("tagline") };
}

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#FFFFFF" },
    { media: "(prefers-color-scheme: dark)", color: "#0C326F" },
  ],
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  return (
    <html lang={locale} className={nunito.variable} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body>
        <NextIntlClientProvider messages={messages} locale={locale}>
          <Header />
          <div id="conteudo">{children}</div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
