# Códigos e base legal das contas públicas

26/11/2026 · explicações do Open Data Brasil · **revisão parcial**.
Integra a ampliação solicitada durante a execução. Não é o catálogo completo de
verbetes da ADR-0035. Não se adotou corte por valor, 50 ações ou 20 órgãos.
A [matriz por domínio/exercício](cobertura-codigos-contas.csv) registra inclusive
domínios sem cadastro integral acessível; quantidade desconhecida fica vazia,
nunca zero. A [ficha 0A53](acao-0A53.md) distingue o cadastro de 2016 do exemplo
financeiro sem período. [Verbetes de referência](verbetes-contas.json) e
[manifestos históricos dos cadastros](cadastros-preservados.json) são separados.

## Cobertura que foi possível demonstrar

Os arquivos SIOP 2024/2025 de ações e PO e TABMUN constam do manifesto de coleta
de 22/11, com tamanho, SHA-256 e identificação da coleta. Esse manifesto foi lido
agora; os cinco arquivos correspondentes não estavam montados nesta execução.
Seus hashes de conteúdo **não foram recalculados**. Isso permite retomar a leitura
integral sem reingerir dados, mas não permite contar códigos ou homologar verbetes.
O número de 5.645 ações em 2025 na ADR-0035 é antecedente, não contagem desta revisão.

A tentativa controlada de obter o CSV de ações de 2024 pela rede local falhou
antes da conexão (resolução DNS, zero bytes); a ferramenta web informou tipo
`text/csv` não suportado. Não houve 403 desse cadastro, nem alteração de identidade,
proxy, credencial ou serviço. Consulta protegida da CGU não foi repetida.
Leitura web dos manuais e das fontes legislativas foi possível em parte.

Foram transcritos 12 verbetes de três tabelas pequenas do MTO 2026: três esferas,
duas categorias econômicas ordinárias e sete GND, incluindo a reserva. Um verbete
adicional identifica a ação 0A53 no cadastro de 2016. **Treze verbetes não cobrem
todos os códigos das contas.** A reserva na categoria econômica merece tratamento
separado; não se afirma que só existam os códigos 3 e 4 em toda natureza de despesa.
Não há contagem atual de códigos observados nas linhas do portal ou correspondências
completas confirmadas nesta execução.

## Domínios e chaves

| Domínio | Chave e relação a preservar | Interpretação / restrição |
|---|---|---|
| Município SIAFI / município IBGE | sistema + código textual + edição/vigência; ponte TABMUN versionada | SIAFI não é IBGE; nome semelhante não autoriza casamento. “Não se aplica” não é município. |
| Órgão superior/órgão SIAFI, UG e gestão | domínio + código + exercício/vigência; parentesco oficial | Órgão orçamentário, órgão administrativo SIORG e UG não são intercambiáveis. |
| Unidade SIORG | código SIORG + versão/data; hierarquia oficial | Mudanças institucionais não são apenas trocas de nome. Correspondência SIAFI exige fonte própria. |
| UO, esfera, função, subfunção, programa e ação SIOP | exercício + esfera + UO + função + subfunção + programa + ação | Código de ação isolado é insuficiente para a ocorrência cadastral. |
| Plano orçamentário / localizador | chave completa da ação + PO ou localizador | PO é detalhamento gerencial; localizador não prova endereço de aplicação de cada pagamento. |
| Natureza da despesa | exercício + categoria + GND + modalidade + elemento + subelemento, quando existente | Não confundir categoria econômica com grupo; não completar códigos ausentes por suposição. |
| Fonte/destinação, tipo de transferência/favorecido | domínio normativo/original + exercício/vigência | Ação, origem de verba, fonte contábil e linguagem cidadã têm significados diferentes. |
| CNAE / natureza jurídica | classificação + versão + código; cadastro PJ datado | Não converter natureza jurídica em classe editorial sem regra versionada; sede não é aplicação. |

O [manual SIOP](https://orcamento.dados.gov.br/siopdoc/doku.php/acesso_publico:dados_abertos_cadastro_acoes),
§§1–5, edição dinâmica consultada em 26/11/2026, sustenta as sete colunas da chave,
relações ação–PO/localizador e campo Base Legal. Códigos têm largura canônica;
ação é alfanumérica. CSV usa `;`, aspas e texto multilinha. Usar leitor CSV real,
conservar cabeçalho e tratar códigos como texto. Layouts e conteúdo mudam por ano.
O encoding precisa ser confirmado nos bytes: a configuração registra cp1252,
mesmo quando o cabeçalho HTTP declara UTF-8; não corrigir silenciosamente o original.

O [MTO 2026, 4ª versão, 23/01/2026](https://www1.siop.planejamento.gov.br/mto/lib/exe/fetch.php/mto2026%3Amto_2026_-_versao_4_.pdf),
§§4.2, 4.3, 4.6.2.1 e tabelas do capítulo 10, foi consultado em 26/11/2026.
Sustenta a separação institucional e a estrutura da natureza. A edição localizada
não foi certificada como última revisão do ano; portarias posteriores precisam
ser incorporadas antes de homologar o cadastro daquele exercício.

O [MGI, módulos SIORG](https://www.gov.br/gestao/pt-br/assuntos/gestaoeinovacao/modelos-organizacionais/estruturas-organizacionais/Sistema-informatizado-siorg/tutorais-sistema-informatizado-siorg/conheca-os-modulos-do-sistema-informatizado-siorg),
seções Consulta Pública/Dados Abertos, e o [manual de consulta da estrutura completa](https://siorg.gov.br/manuais/manual-webservices/html/demo_5.html),
parâmetros e retorno, foram localizados por pesquisa oficial indexada em 26/11/2026.
Não houve chamada à API de estruturas nem download integral; quantidade, vigências
e correspondências continuam pendentes. A [TABMUN do Tesouro](https://www.tesourotransparente.gov.br/ckan/dataset/lista-de-municipios-do-siafi)
tem identificação/linhagem na configuração, mas a abertura web desta revisão não
substituiu a leitura dos registros. O nome de um sistema não é chave universal.

## Origens de recursos e legislação

O vínculo normativo precisa de dois níveis: (1) a norma citada pelo cadastro;
(2) a confirmação da redação, dispositivo e aplicabilidade ao período de cada
lançamento. O primeiro pode estar comprovado enquanto o segundo permanece pendente.
Texto compilado atual não representa automaticamente todas as redações históricas.

| Origem | Evidência independente e o que sustenta | O que não ficou resolvido |
|---|---|---|
| Participações de petróleo/gás | [Lei 9.478/1997](https://www.planalto.gov.br/ccivil_03/leis/l9478compilado.htm), arts. 45 e 47–50: espécies e mecanismos distintos; cadastro 0A53/2016 relaciona arts. 48–50 e fundo especial | Redação e eventual suspensão judicial aplicáveis ao exercício do exemplo; decomposição do valor entre espécies. |
| Royalties | [ANP, Royalties](https://www.gov.br/anp/pt-br/assuntos/royalties-e-outras-participacoes/royalties), seção inicial/Fórmula, atualização 29/10/2026: apuração mensal por alíquota × valor da produção; esta combina volumes e preços de referência de petróleo/gás | Regime contratual, alíquota e parâmetros de cada campo, competência × data de repasse e rateio por beneficiário. A faixa geral ANP não é taxa única do art. 47 da concessão. |
| FPM/FPE | [LC 62/1989](https://www.planalto.gov.br/ccivil_03/leis/lcp/lcp62.htm), art. 1º: cálculo, entrega e controle dos fundos, remetendo à CF, arts. 159/161 | Coeficientes TCU anuais, alterações constitucionais, parcelas adicionais e retenções de cada pagamento; a conferência não calcula direitos de um município. |
| Fundeb | [Lei 14.113/2020](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2020/lei/l14113.htm), arts. 1º e 7º: fundos e distribuição com matrículas/ponderações; [FNDE, normas 2026](https://www.gov.br/fnde/pt-br/acesso-a-informacao/acoes-e-programas/financiamento/fundeb/legislacao/2026/): atualizações das modalidades VAAF/VAAT/VAAR | Portaria/fatores vigentes em cada competência, natureza do lançamento e enquadramento da ação naquele ano; não usar regra de 2016 no fundo permanente. |
| Demais origens | Dicionários CGU identificam campos; o cadastro completo deve enumerar todas as origens observadas | Não há nesta execução enumeração integral dos recebimentos/origens; ITR, IPI-exportação, CIDE, salário-educação e outras não recebem fundamentação inventada. |

Todas as consultas desta seção datam de 26/11/2026; leitura de trechos oficiais,
sem homologação jurídica de cada lançamento. A abertura da Lei 7.525/1986 foi
indisponível na ferramenta: sua relação com a 0A53 está comprovada no cadastro,
mas o texto e a vigência do art. 6º não foram revalidados diretamente.

## Como fechar a revisão sem amostragem por valor

1. Recuperar, em leitura, os cinco cadastros já coletados e conferir seus hashes
   contra o manifesto. Não reingerir ou reprocessar fatos para ler documentação.
2. Enumerar todas as linhas/chaves dos cadastros, por exercício, preservando
   versões, descontinuados e valores especiais. Recuperar os demais exercícios
   do acervo e referências de programas/PPA/localizadores/classificadores.
3. Enumerar códigos distintos observados em cada base/lente, incluindo vazios e
   especiais, sem corte de ranking. Confrontar conjuntos observados × cadastro
   completo, por domínio/exercício; quantificar órfãos, duplicações e ambiguidades.
4. Resolver cada relação por chave oficial. Múltiplas ocorrências de ação não são
   conflito por si; códigos iguais em sistemas distintos não são correspondência.
5. Para todas as origens identificadas, separar base legal do cadastro, norma
   instituidora, regulamentos, alterações e aplicação ao período; registrar
   conflito/indisponibilidade e deixar sem explicação conclusiva quando necessário.
6. Publicar matriz de completude e reconciliar com o manifesto atual, após revisão
   do mantenedor. Esta proposta não autoriza criação/ativação de catálogo ou guia.

A [especificação Excel](../../development/especificacao-excel-rastreavel.md)
acrescenta vínculos explícitos dados → código/domínio/exercício → norma/dispositivo.
Não acrescenta normas como se fossem novas medidas ou parcelas monetárias.
