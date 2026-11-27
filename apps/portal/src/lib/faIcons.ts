// Ícones Font Awesome Free 6.7.2 (sólido), padrão do Design System do gov.br (ADR-0039, seção 7).
// Licença dos ícones: CC BY 4.0 (https://fontawesome.com/license/free); atribuição em
// assets/icons/LICENSE-font-awesome.txt e na página Sobre. Só entram os ícones usados:
// cada um é importado individualmente, sem webfont nem CSS externo.
import {
  faArrowsRotate, faBolt, faBriefcase, faBuilding, faBuildingColumns, faCartShopping, faChartColumn,
  faChartLine, faCircleQuestion, faCity, faFaucetDrip, faFileInvoiceDollar, faFileLines, faGraduationCap,
  faHandHoldingDollar, faHandHoldingHeart, faHandshake, faHandsHoldingChild, faHeartPulse, faHelmetSafety,
  faHouse, faIndustry, faLandmark, faLandmarkFlag, faLayerGroup, faLock, faMobileScreen, faMoneyBillTransfer,
  faPersonCane, faPiggyBank, faRoad, faShieldHalved, faStore, faTag, faTree, faUser, faUserTie, faUsers,
  faVault, faWheatAwn, faEarthAmericas, faTractor, faMasksTheater, faFlask, faScaleBalanced, faGlobe,
  faJetFighter, faFutbol, faTowerBroadcast, faGavel, faPeopleGroup,
  type IconDefinition,
} from "@fortawesome/free-solid-svg-icons";

export interface FaDef {
  /** Nome oficial no Font Awesome (ex.: "heart-pulse"). */
  name: string;
  w: number;
  h: number;
  d: string;
}

function def(i: IconDefinition): FaDef {
  const [w, h, , , d] = i.icon;
  return { name: i.iconName, w, h, d: Array.isArray(d) ? d.join(" ") : d };
}

export const FA = {
  // Blocos e lente
  estatisticas: def(faChartColumn),
  contas: def(faMoneyBillTransfer),
  transferidos: def(faArrowsRotate),
  recebimento: def(faHandHoldingDollar),
  execucao: def(faFileInvoiceDollar),
  // Temas das Estatísticas oficiais
  pessoas: def(faUsers),
  registro: def(faFileLines),
  casa: def(faHouse),
  gota: def(faFaucetDrip),
  educacao: def(faGraduationCap),
  trabalho: def(faBriefcase),
  saude: def(faHeartPulse),
  consumo: def(faCartShopping),
  tecnologia: def(faMobileScreen),
  seguranca: def(faShieldHalved),
  agro: def(faWheatAwn),
  industria: def(faIndustry),
  construcao: def(faHelmetSafety),
  comercio: def(faStore),
  servicos: def(faHandshake),
  empresas: def(faBuilding),
  precos: def(faTag),
  contasNacionais: def(faChartLine),
  ambiente: def(faTree),
  gestao: def(faBuildingColumns),
  generico: def(faLayerGroup),
  // Funções de governo (contas: composição por área)
  assistencia: def(faHandsHoldingChild),
  previdencia: def(faPersonCane),
  defesa: def(faJetFighter),
  transporte: def(faRoad),
  urbanismo: def(faCity),
  organizacaoAgraria: def(faTractor),
  cultura: def(faMasksTheater),
  desporto: def(faFutbol),
  energia: def(faBolt),
  comunicacoes: def(faTowerBroadcast),
  ciencia: def(faFlask),
  relacoesExteriores: def(faGlobe),
  judiciaria: def(faScaleBalanced),
  justica: def(faGavel),
  cidadania: def(faPeopleGroup),
  encargos: def(faLandmark),
  // Classes de favorecido
  municipio: def(faCity),
  estado: def(faLandmarkFlag),
  fundo: def(faPiggyBank),
  entidade: def(faHandHoldingHeart),
  financeira: def(faVault),
  pessoa: def(faUser),
  pessoaCnpj: def(faUserTie),
  internacional: def(faEarthAmericas),
  sigiloso: def(faLock),
  semInformacao: def(faCircleQuestion),
} satisfies Record<string, FaDef>;

export type FaName = keyof typeof FA;
