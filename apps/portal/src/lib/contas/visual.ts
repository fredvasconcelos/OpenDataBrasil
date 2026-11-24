// Ícone e família de cor por função de governo e por classe de favorecido (ADR-0039).
// A cor fica só no quadro do ícone, nunca nos dados (barras e mapa usam as cores de gráfico).
import { FA, type FaDef } from "@/lib/faIcons";
import type { ThemeFamily } from "@/lib/themes";

interface Visual {
  icon: FaDef;
  family: ThemeFamily;
}

// Códigos da classificação funcional (Portaria MOG 42/1999). A mesma família do tema
// equivalente nas Estatísticas oficiais: Saúde é magenta nos dois blocos.
const FUNCTIONS: Record<string, Visual> = {
  "01": { icon: FA.gestao, family: "ardosia" },
  "02": { icon: FA.judiciaria, family: "ardosia" },
  "03": { icon: FA.justica, family: "ardosia" },
  "04": { icon: FA.gestao, family: "petroleo" },
  "05": { icon: FA.defesa, family: "ardosia" },
  "06": { icon: FA.seguranca, family: "ardosia" },
  "07": { icon: FA.relacoesExteriores, family: "azul" },
  "08": { icon: FA.assistencia, family: "laranja" },
  "09": { icon: FA.previdencia, family: "azul" },
  "10": { icon: FA.saude, family: "magenta" },
  "11": { icon: FA.trabalho, family: "laranja" },
  "12": { icon: FA.educacao, family: "roxo" },
  "13": { icon: FA.cultura, family: "roxo" },
  "14": { icon: FA.cidadania, family: "azul" },
  "15": { icon: FA.urbanismo, family: "petroleo" },
  "16": { icon: FA.casa, family: "ocre" },
  "17": { icon: FA.gota, family: "petroleo" },
  "18": { icon: FA.ambiente, family: "verde" },
  "19": { icon: FA.ciencia, family: "azul" },
  "20": { icon: FA.agro, family: "verde" },
  "21": { icon: FA.organizacaoAgraria, family: "verde" },
  "22": { icon: FA.industria, family: "ardosia" },
  "23": { icon: FA.comercio, family: "roxo" },
  "24": { icon: FA.comunicacoes, family: "azul" },
  "25": { icon: FA.energia, family: "ocre" },
  "26": { icon: FA.transporte, family: "ardosia" },
  "27": { icon: FA.desporto, family: "verde" },
  "28": { icon: FA.encargos, family: "ardosia" },
};

const CLASSES: Record<string, FaDef> = {
  municipio: FA.municipio,
  estado_df: FA.estado,
  fundo_municipal: FA.fundo,
  fundo_estadual: FA.fundo,
  fundo_federal: FA.fundo,
  outro_ente_publico: FA.gestao,
  empresa: FA.empresas,
  entidade_sem_fins_lucrativos: FA.entidade,
  instituicao_financeira: FA.financeira,
  pessoa_fisica_com_cnpj: FA.pessoaCnpj,
  organizacao_internacional: FA.internacional,
  pessoa_fisica: FA.pessoa,
  pessoa_fisica_sem_cpf: FA.pessoa,
  exterior: FA.internacional,
  unidade_gestora_federal: FA.gestao,
  sigiloso: FA.sigiloso,
};

const OTHER: Visual = { icon: FA.generico, family: "ardosia" };

export function functionVisual(code: string): Visual {
  return FUNCTIONS[code.padStart(2, "0")] ?? OTHER;
}

export function classIcon(recipientClass: string): FaDef {
  return CLASSES[recipientClass] ?? FA.semInformacao;
}
