# ADR-0038: FPM do Tesouro como segunda fonte da lente A

- **Estado:** aceito (2026-11-22). O mantenedor pediu "Vamos fechar a segunda fonte para o
  FPM" e aprovou três decisões: o complemento, a correção do SIAFI 4196 para Boa Esperança
  do Norte e a licença ODbL.
- **Contexto normativo:** CLAUDE.md §7.3, §9.4, §13.3, §16.2, §17.4 e §23; ADR-0028
  (licenças), ADR-0030 (lentes), ADR-0032 (território), ADR-0036 (Gold e situação do mês).

## Contexto

Na lente A da CGU, faltam as parcelas adicionais de 1% do FPM (julho, setembro e
dezembro) desde 2025, de R$ 7,8 bi a R$ 10,1 bi por mês. Em 2026-10, falta o FPM inteiro.
O total pago está na lente C, mas sem município, e repartir esse valor sem fonte seria uma
redistribuição arbitrária (§13.3). O ADR-0036 marcou esses meses como "incompletos".

O Tesouro publica a distribuição do FPM por município. Há três caminhos:

| Caminho | Chave do município | Situação em 2026-11-22 |
|---|---|---|
| CKAN, "Transferências Obrigatórias da União – por Município", recurso **"FPM por município"** (CSV de 30 MB, série mensal desde 1996) | **código SIAFI** (`COD_MUN`) | escolhido |
| CKAN, "Transferências Constitucionais para Municípios" (um CSV por mês, por decêndio, com a linha "FPM 1%" separada) | só **nome e UF** | 108 dos 5.570 nomes não batem exatamente com o IBGE; casar seria por semelhança (proibido) |
| API `apiapex.tesouro.gov.br/.../transferencias_constitucionais` (`co_ibge`, `co_siafi`) | IBGE e SIAFI | responde 404 ("Serviço não encontrado"), e a documentação, 403. Não contornar (§7.3) |

**Conferência do arquivo escolhido com a lente A** (ação 0045, por município e mês):
- 2024: os 5.569 municípios iguais ao centavo em todos os meses;
- 2025–2026, meses comuns: 99,96% iguais ao centavo. As diferenças são só o SIAFI 4196 e
  o 1182 (abaixo);
- meses das parcelas adicionais: o Tesouro tem o FPM com a parcela de 1%, e os totais
  batem com o pago na lente C. Por exemplo, em 2026-09: R$ 22,469 bi no Tesouro, R$ 12,377 bi
  na lente A e R$ 22,47 bi na lente C;
- o arquivo está líquido da retenção do FUNDEB, como a lente A. A parcela de 1% não tem
  retenção. O CSV mensal confirma a soma: em 2026-09, "FPM" dá R$ 12,3765 bi e "FPM 1%",
  R$ 10,0927 bi.

**Achado:** as 3 linhas do SIAFI 4196 "CACHOEIRA DO PAJEU"/MG são o FPM e a CIDE de Boa
Esperança do Norte/MT (ADR-0032, decisão 1, revisada).

## Decisões

1. **Fonte:** o recurso "FPM por município" (`tesouro-fpm-municipio`), ingerido como
   arquivo inteiro. O Tesouro republica a série todo mês e revisa até o início do
   exercício. Cada versão fica na Bronze pelo checksum, e a Silver é substituída por
   inteiro a cada versão.
2. **Silver `stn/tesouro_fpm_municipality`:**
   - o arquivo largo (um ano por coluna) vira uma linha por município e mês;
   - `-` é mês sem repasse: não vira linha nem zero (§9.4);
   - o valor aceita o negativo contábil entre parênteses ("(180.529,62)", dois casos, em
     2001 e 2004);
   - o município vem do SIAFI pela TABMUN e, fora dela, do nome + UF exatos da DTB, a mesma
     regra da lente A (ADR-0032). Boa Esperança do Norte (`1182`) entra assim;
   - nenhum município pode ficar sem resolução, e o original fica em `value_raw`.
3. **Complemento na Gold:**
   - **Quando:** num mês da lente A em que o FPM total fica abaixo do Tesouro além da
     tolerância por ação do ADR-0036 (1% ou R$ 1 mi, o que for maior).
   - **O quê:** em cada município desse mês, uma linha com a diferença
     `Tesouro − lente A`, marcada `value_source = "tesouro_fpm"` no fato
     `fact_federal_transfer` 1.2.0. As demais linhas têm `value_source = "cgu"`.
   - **Atributos da linha:** favorecido, UG, ação e natureza copiados da linha de FPM da
     prefeitura no mês mais recente até aquele (ou no primeiro depois). Assim, ranking,
     "detalhar por" e ficha tratam o complemento como FPM da prefeitura.
   - **Meses que não mudam:** nos demais, nada muda. Uma diferença por município fora de um
     mês complementado só é registrada.
   - **Recálculo:** o complemento é refeito a cada build. Se a CGU completar um mês depois,
     ele some sozinho.
   - **Situação do mês:** a conferência A × C já inclui o complemento. A nota da situação
     do mês (`agg_contas_period_status` 1.1.0, coluna `complement_value`) diz quanto veio
     do Tesouro e cita a fonte.
4. **Conferência gravada:** `agg_fpm_reconciliation` tem, por município e mês, a lente A, o
   Tesouro, o complemento e a situação (`conferido`, `complementado` ou `divergente`).
5. **Verificações da Gold:**
   - **bloqueiam:**
     - complemento negativo (o Tesouro abaixo da lente A num mês complementado);
     - município complementado sem linha de FPM da prefeitura para copiar;
   - **avisam:** as divergências nos meses não complementados.
6. **Licença ODbL** (`tesouro-odbl`, aprovada em 2026-11-22):
   - pede atribuição ("Fonte: Tesouro Nacional (Tesouro Transparente)") e compartilhamento
     pela mesma licença para bases derivadas;
   - pelo ADR-0028, os dados seguem a licença da fonte, então os agregados da lente A com
     complemento citam a ODbL;
   - a API mostra o crédito no aviso da lente A e na nota dos meses complementados.
7. **SIAFI 4196:** a correção aponta para Boa Esperança do Norte (5101837), pela evidência
   do Tesouro (ADR-0032, decisão 1). A atribuição anterior, a Cachoeira de Pajeú, foi
   revogada.

## Consequências

- Os meses das parcelas adicionais e 2026-10 passam a ter o FPM por município. Continuam
  "incompletos" os meses com outras lacunas na fonte: salário-educação em 2025-12 e
  2026-03, e Piso da Atenção Primária em 2025-07.
- A Gold do escopo `contas` passa a depender de mais uma Silver (`tesouro-fpm-municipio`).
  A atualização mensal deve ingerir o arquivo do Tesouro junto com as lentes da CGU.
- O FPE e as demais transferências constitucionais (ITR, CIDE, royalties) têm arquivos
  equivalentes no mesmo conjunto do Tesouro. Ficam fora deste ADR: a lente A não tem lacuna
  conhecida nelas.

## Resultados (build local de 2026-11-22)

- **Silver:** `tesouro-fpm-municipio` com 2.049.384 linhas (1996-01 a 2026-10). Todos os
  municípios foram resolvidos, sem nenhum valor fora do formato. A lente A foi refeita
  (v139) com a correção do SIAFI 4196.
- **Gold:** build `f85e7a1e`, 63 verificações aprovadas e 2 avisos. Release candidato
  **`e8bb048c`**, `validated` e **não ativado**.
- **Conferência por município e mês** (`agg_fpm_reconciliation`, 2024-01 a 2026-11):

  | Situação | Linhas |
  |---|---:|
  | conferido ao centavo | 155.946 |
  | complementado | 33.420 |
  | divergente | 2 |

  As 2 divergentes são Boa Esperança do Norte em 2025-01 e 2025-02. Nesses meses, a CGU
  registrou o FPM como favorecido "INVÁLIDO", sem UF, e o valor conta só no Brasil.
- **Complemento** (5.570 municípios por mês, nenhum negativo):

  | Mês | Complemento |
  |---|---:|
  | 2025-07 | R$ 9,16 bi |
  | 2025-09 | R$ 7,83 bi |
  | 2025-12 | R$ 9,45 bi |
  | 2026-07 | R$ 9,95 bi |
  | 2026-09 | R$ 10,09 bi |
  | 2026-10 | R$ 12,58 bi |
  | **Total** | **R$ 59,07 bi** |
- **Situação dos meses da lente A:**
  - eram 7 incompletos e passaram a 2:
    - 2026-03, pelo salário-educação;
    - 2026-10, em que ainda faltam o FPE e o FUNDEB;
  - 2025-07, 2025-09, 2025-12, 2026-07 e 2026-09 passaram a fechados. A maior falta
    restante entre eles é a de 2025-12, com 4,37%.
- **API local sobre o candidato:**
  - em 2026-09, o FPM de Acrelândia/AC é R$ 1.974.079,84, igual ao Tesouro, e o mapa não é
    mais parcial;
  - em 2025-03, Cachoeira de Pajeú tem só o próprio FPM (R$ 1.076.784,47), e a linha do
    SIAFI 4196 aparece em Boa Esperança do Norte.
