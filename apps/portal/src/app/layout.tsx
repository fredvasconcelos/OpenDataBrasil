import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages, getTranslations } from "next-intl/server";

import { Header } from "@/components/Header";

import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("site");
  return { title: t("name"), description: t("tagline") };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  return (
    <html lang={locale}>
      <body>
        <NextIntlClientProvider messages={messages} locale={locale}>
          <Header />
          <div id="conteudo">{children}</div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
