# ADR-0032: Território das contas públicas — SIAFI→IBGE, sede e agregação regional

- **Estado:** aceito (2026-11-22). A regra de região vem do pedido do mantenedor: "a região
  é a junção dos seus estados e municípios pela nossa dimensão de território".
- **Contexto normativo:** CLAUDE.md §13 e §15.4; ADR-0023, decisão 1 (regiões pela soma
  das UFs); ADR-0030.

## Contexto

- A lente A traz o **código SIAFI** do município. A TABMUN do Tesouro (CKAN
  `lista-de-municipios-do-siafi`, de 2021-12-21: SIAFI, CNPJ da prefeitura, nome, UF e
  IBGE) casou 5.570 dos 5.571 códigos de 2025-10. Ficaram de fora `1182` Boa Esperança do
  Norte/MT (município novo) e `-14` "Múltiplo".
- A lente B traz **UF e nome** do município da sede do favorecido, sem código. Com a união
  dos nomes IBGE e TABMUN normalizados, sobram `EX`/Exterior, `-1`/"Sem informação" e duas
  renomeações oficiais do RN: Presidente Juscelino → Serra Caiada e Augusto Severo →
  Campo Grande.
- **Nenhuma das bases tem nível de região.** Também não há código IBGE na lente B.

## Decisões

1. **Município na lente A:** SIAFI → IBGE pela TABMUN. Os municípios ausentes entram num
   suplemento versionado, com a fonte de cada linha (código IBGE oficial e ato de
   instalação). Um código sem casamento bloqueia a Silver.
   - **Correções aprovadas (2026-11-22):** um erro da fonte, confirmado pelo mantenedor,
     entra numa lista explícita na configuração da lente (`territory_corrections`). Cada
     entrada tem UF, SIAFI, nome exato da fonte, código IBGE de destino, motivo e
     aprovação. O casamento é por **igualdade** das três chaves (depois da normalização de
     acento e caixa), nunca por semelhança. O SIAFI oficial da TABMUN sempre vence, e o
     destino precisa existir na DTB. A linha fica com
     `territory_method = "correcao_aprovada"`. A lista entra no rótulo das referências:
     mudar uma correção refaz os meses. A lista só vale para a lente A; nas outras lentes,
     a Silver a recusa.
   - **O destino vem de evidência oficial, nunca do nome** (revisão de 2026-11-22,
     ADR-0038): o valor igual ao centavo numa segunda fonte com código. O destino pode
     estar noutra UF: o município manda na UF da linha.
   - **Caso real:** SIAFI `4196` "CACHOEIRA DO PAJEU"/MG, fora da TABMUN. São 3 linhas, de
     2025-03 e 2025-04: duas de FPM e uma da cota da CIDE, com R$ 1,65 mi, pagas a uma
     empresa (TV Filme Serviços de Telecomunicações Ltda., sede em Brasília/DF).
     - **Primeira decisão (revogada):** pela semelhança com `4053` "CACHOEIRA DE PAJEU"
       (IBGE 3102704), propus Cachoeira de Pajeú/MG, e a grafia foi confirmada pelo
       mantenedor. Foi um erro: a atribuição se apoiou no nome.
     - **Decisão vigente (aprovada em 2026-11-22):** **Boa Esperança do Norte/MT
       (5101837)**. No Tesouro ("FPM por município" e "CIDE por município"), os três
       valores são, ao centavo, o FPM e a CIDE do SIAFI `1182` Boa Esperança do Norte
       nesses meses (813.837,58; 826.997,85; 5.612,79). 813.837,58 é a cota dos municípios
       de coeficiente 0,6 de MT naquele mês; a de MG foi 1.076.784,47, exatamente o que
       Cachoeira de Pajeú (`4053`) recebeu. Em 2025-01 e 2025-02, o mesmo FPM aparece na
       lente A como favorecido "INVÁLIDO", sem UF, e fica só no Brasil. A partir de 2025-05,
       vem com o código 1182. Os valores contam no território de Boa Esperança do Norte,
       com a classe "empresa" do favorecido da fonte.
   - **Teto de não resolvidos (ajuste da CP2, aprovado em 2026-11-22: "Mantém o teto de
     10"):** o bloqueio vale acima de `max_unresolved_territory` linhas por mês (10, na
     configuração de cada lente). Até esse teto, a linha fica com `territory_status = "nao_resolvido"`,
     entra no total da UF e do Brasil, fica fora do mapa municipal e gera aviso com a lista
     dos casos. Depois da correção acima, a lente A não tem nenhuma linha não resolvida
     em 2024-01 a 2026-11.
2. **Município na lente B:** UF + nome normalizado (sem acento, caixa alta, espaços únicos)
   contra os nomes IBGE ∪ TABMUN. Uma tabela de aliases cobre as renomeações oficiais,
   cada uma com a fonte do IBGE. Exige 100% de casamento, exceto os estados especiais.
3. **Estados especiais, explícitos e fora do mapa:**
   - `EX` Exterior;
   - `-1` Sem informação;
   - `-14` Múltiplo;
   - favorecidos estaduais e federais sem município, que ficam no nível UF ou Brasil.

   Esses valores entram nos totais do Brasil (e da UF, quando houver) e aparecem como
   "sem município" ou "exterior".
4. **Região e Brasil pela `dim_geography`:** a região é a soma das UFs, e a UF é a soma dos
   seus municípios mais os favorecidos estaduais sem município. É a mesma regra do
   ADR-0023 (primeiro dígito do código da UF, DTB fixada), com status `derived_sum`. As
   fontes não publicam região.
5. **O território do valor é o do favorecido, não o do serviço.** A lente A usa o ente,
   fundo ou entidade recebedora. A lente B usa a sede cadastral: uma empresa de SP que
   executa obra no PA aparece em SP. As duas regras vão em nota visível no mapa e na ficha.
   - **Estratégia futura** (pedido do mantenedor, 2026-11-22): associar o favorecido ao
     **local de aplicação** do recurso, para responder "quanto dinheiro recebeu cada
     localidade e como foi empenhado". Os caminhos candidatos estão no plano de contas
     públicas, seção 15. Até lá, nenhum valor muda de território por inferência: a
     associação só entra com fonte oficial que ligue o pagamento ao local, e com ADR
     próprio.
6. **O localizador da lente C não entra no mapa.** Em 2025-10, ele vinha vazio em 93% do
   valor pago (R$ 403,8 bi de R$ 433,0 bi).
7. **Ranking contextual** (ADR-0034): "favorecidos do estado X" inclui todos os
   favorecidos dos municípios de X, mais os estaduais sem município. A filtragem usa o
   prefixo do código IBGE (região = 1 dígito, UF = 2 dígitos), que permite poda de
   partições.
