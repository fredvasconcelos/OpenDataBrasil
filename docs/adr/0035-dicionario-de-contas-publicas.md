# ADR-0035: Dicionário de contas públicas

- **Estado:** aceito (2026-11-22), a pedido do mantenedor: "um grande dicionário para
  fornecer ao usuário todos os detalhes possíveis sobre os programas, órgãos e o que
  significam [...] fundo dos municípios, o que é e para que serve". As licenças das fontes
  aguardam aprovação (ADR-0030, decisão 6).
- **Contexto normativo:** CLAUDE.md §3.2 (não inventar), §12.2 (catálogo no PostgreSQL),
  §15, §19.4 e §19.5 (i18n); ADR-0028 (textos em CC BY 4.0).

## Contexto

Os arquivos da CGU trazem só código e nome. Os catálogos da API também: em
`funcional-programatica/programas`, os nomes vêm com a codificação quebrada na própria
fonte ("SAZDE DA FAMMLIA"). As descrições precisam vir de fontes oficiais próprias.
Verificado em 2026-11-22:

| Verbete | Fonte oficial | Conteúdo | Estado |
|---|---|---|---|
| Ação orçamentária | SIOP, cadastro de ações (CSV por exercício, 2010–2026: `dados_acao{ano}.csv`, 5.645 ações em 2025) | título, tipo, descrição, base legal, beneficiário, forma de implementação, produto | **verificado** (ex.: 0045 FPM: "22,5% da arrecadação do IR e IPI + EC 55, 84 e 112"; base legal CF art. 159 e LC 62/1989) |
| Plano orçamentário | SIOP, `dados_plano_orcamentario{ano}.csv` | título, detalhamento | a ler na CP1 |
| Programa | PPA 2024–2027 no dados.gov.br (MPO); SPARQL do SIOP | objetivo, público-alvo, órgão responsável | a localizar na CP1 |
| Órgão | SIORG (estrutura organizacional, API `estruturaorganizacional.dados.gov.br`) e nomes do SIAFI | natureza, sigla, hierarquia, vinculação, competências quando houver | o host não respondeu em 22/11; a verificar |
| Função, subfunção | Portaria MOG nº 42/1999; Manual Técnico do Orçamento (MTO) | conceitos | a ler |
| Grupo, modalidade, elemento | Portaria Interministerial STN/SOF nº 163/2001, Anexo II; dicionários da CGU | definição de cada código | a ler |
| Fases e termos (empenho, liquidação, pagamento, restos a pagar, convênio, transferência voluntária, fundo a fundo, transferência especial) | Lei 4.320/1964; LRF; LDO 2026; dicionários e glossário da CGU | definições legais | **verificado** para os artigos citados no ADR-0033 |
| Transferências constitucionais (FPM, FPE, FUNDEB, ITR, royalties, salário-educação, IPI-exportação) | CF arts. 157–162; LC 62/1989; Lei 14.113/2020; cadastro de ações do SIOP; publicações do Tesouro | o que é, quem recebe, critério de rateio, para que serve | parcial (FPM pelo SIOP) |
| Natureza jurídica, CNAE | tabela de natureza jurídica do cadastro PJ da CGU (Receita/CONCLA); CNAE 2.0 (IBGE/CONCLA) | descrição oficial | verificado (o arquivo vem no zip `favorecidos-pj`) |

## Decisões

1. **Duas camadas de texto, sempre separadas e identificadas:**
   - **texto oficial:** copiado da fonte, sem edição (descrição e base legal do SIOP,
     artigo de lei, definição da CGU), com a fonte, a URL, o exercício e a data da coleta.
     O rótulo é "texto oficial";
   - **explicação do portal:** linguagem simples, curta, escrita pela equipe a partir do
     texto oficial, com as citações. O rótulo é "explicação do Open Data Brasil", em
     CC BY 4.0 (ADR-0028). Ela nunca acrescenta um fato que o texto oficial não sustente.
2. **Estrutura do verbete** (catálogo no PostgreSQL, gerado de configuração versionada; não
   é dado da Gold):
   - `tipo`, `codigo` e `exercicio` (os códigos de programa e ação mudam de sentido entre
     PPAs);
   - `nome_oficial`, `texto_oficial`, `base_legal`;
   - `explicacao`, `exemplos`, `relacionados`;
   - `fonte_url`, `coletado_em` e licença.
3. **Prioridade de escrita das explicações:**
   1. tipos de transferência e transferências constitucionais (FPM, FPE, FUNDEB…);
   2. fases da despesa e termos;
   3. fundos (o que é um Fundo Municipal de Saúde, de Assistência Social, o FNDE e o FNS);
   4. as funções;
   5. as 50 maiores ações e os 20 maiores órgãos por valor do piloto.

   O restante fica só com o texto oficial.
4. **Integração no portal:**
   - cada código exibido (no tooltip, no "detalhar por", na tabela e na ficha) tem um link
     "o que é isto?" para o verbete;
   - uma página de dicionário com busca;
   - textos por next-intl, prontos para tradução (§19.5).
5. **Não inventar (§3.2):** sem fonte oficial localizada, o verbete fica só com o nome
   oficial e a marca "descrição oficial não localizada". Nada é preenchido por suposição.
6. **Atualização:** o cadastro do SIOP é relido a cada exercício novo e a cada revisão. O
   verbete mostra o texto do exercício do dado exibido.
