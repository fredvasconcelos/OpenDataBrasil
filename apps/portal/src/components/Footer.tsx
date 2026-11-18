"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

import { Logo } from "@/components/Logo";
import { ProjectLinks } from "@/components/ProjectLinks";

// Rodapé (Design System ODBr, seção 8; DS 2.10): fundo marinho nos dois temas, logo com as
// cores do negativo; à direita, "Sobre os dados" e "Apoie o projeto" em texto e, depois de
// um separador, Contato (e-mail), Instagram e GitHub como ícones. O idioma fica só no
// cabeçalho. No Painel de análise usa a faixa fina de 44 px ("slim"), sem "Sobre os
// dados", para não roubar altura do mapa, do gráfico e da tabela.
export function Footer() {
  const t = useTranslations();
  const path = usePathname();
  const slim = path?.startsWith("/dashboard") ?? false;
  return (
    <footer className={slim ? "footer slim" : "footer"}>
      <div className="footer-brand">
        <Logo size={slim ? 18 : 26} label={t("site.name")} />
        <span aria-hidden="true">{t("site.name")}</span>
      </div>
      <nav aria-label={t("nav.footer")}>
        {slim ? null : <Link href="/sobre">{t("nav.about")}</Link>}
        <Link href="/apoie">{t("nav.supportLong")}</Link>
        <span className="footer-sep" aria-hidden="true" />
        <span className="footer-social" role="group" aria-label={t("nav.links")}>
          <ProjectLinks variant="footer" />
        </span>
      </nav>
    </footer>
  );
}
