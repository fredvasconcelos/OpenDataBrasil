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
6. **O localizador da lente C não entra no mapa.** Em 2025-10, ele vinha vazio em 93% do
   valor pago (R$ 403,8 bi de R$ 433,0 bi).
7. **Ranking contextual** (ADR-0034): "favorecidos do estado X" inclui todos os
   favorecidos dos municípios de X, mais os estaduais sem município. A filtragem usa o
   prefixo do código IBGE (região = 1 dígito, UF = 2 dígitos), que permite poda de
   partições.
