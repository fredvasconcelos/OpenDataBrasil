# ADR-0022: Séries compostas de fontes distintas

- **Estado:** aceito (2026-11-13), por decisão do mantenedor: quando fontes diferentes
  (Censo Demográfico, PNAD Contínua e as que vierem) se complementam, a série pode ser
  composta. As notas precisam dizer que a variável tem fontes distintas e como a série
  foi construída.
- **Amplia:** ADR-0016 (séries de tabelas), ADR-0018 (tabelas-irmãs) e ADR-0021
  (edições).
- **Contexto normativo:** CLAUDE.md §15.4 (compatibilidade "mediante transformação
  documentada"), §15.5, §16.2 e §28.5.

## Contexto

Censo e PNAD Contínua medem vários assuntos em comum (esgoto, lixo, alfabetização), com
métodos diferentes. No ano em comum (2022), os valores do Brasil diferem de 0,5 a 4,6
pontos percentuais ([fontes-comparaveis.md](../data_catalog/fontes-comparaveis.md)).
Com mais fontes no portal, esses casos vão se multiplicar.

## Decisões

1. **Série composta permitida** quando as fontes medem o mesmo conceito, com
   categorias harmonizáveis, e se complementam no tempo ou no território.
2. **Uma fonte por célula:** cada combinação de território, período e categoria vem
   de uma fonte só. Num ano coberto por duas, a configuração declara a principal; a
   outra fica fora da série (e pode aparecer como comparação).
3. **Transformações documentadas na regra da tabela** (`table_rules`, ADR-0016):
   - categorias por `recode_categories` e `rename_dimensions`;
   - mudança de escala (mil unidades → unidades) e complemento (analfabetismo →
     alfabetização, 100 − x) entram como transformações novas, com teste;
   - diferença de universo (ex.: domicílios só com banheiro na PNAD) vai para a nota.
4. **Nota automática:** o gerador escreve "Fontes distintas (ADR-0022)" sempre que os
   membros de uma série vêm de pesquisas diferentes (`Pesquisa` do descritor). A nota
   diz quais pesquisas, em quais tabelas, e avisa que a troca de fonte pode mudar o
   nível da série sem mudança real. Séries curadas à mão levam a mesma nota.
5. **Não compor:**
   - universos diferentes sem um recorte comum (instrução de 18 anos ou mais × 25 anos
     ou mais);
   - quesitos diferentes (água: ligação à rede × principal fonte);
   - soma ou comparação entre fontes dentro do mesmo período e nível.
6. **Portal (a fazer):** o gráfico de evolução marca a troca de fonte (marcador
   diferente e legenda "Fonte: …" por trecho), e o tooltip diz a fonte do ponto.

## Consequências

- **Nota no gerador:** feita (`multi_source_note`, com teste). As séries atuais têm uma
  pesquisa só, então nenhuma nota nova apareceu.
- **Primeiras séries compostas candidatas:** esgoto, lixo e alfabetização (Censo + PNAD).
  Dependem das transformações de escala e de complemento (decisão 3) e da marcação no
  gráfico (decisão 6).

## Atualização (2026-11-13): implementação

- **Série composta declarada** em `configs/sources/compostas.toml` (`[[series]]` com os
  membros). Diferente de `silver.series`, um dataset pode servir o próprio indicador e
  várias séries compostas (a 9543 é série com a 9841 e membro da composta da
  alfabetização).
- **Transformações na regra da tabela** (`table_rules`): `variable`, `levels`,
  `exclude_periods`, `scale`, `complement`, `unit`, `aggregate` (soma numa
  categoria-alvo, com valor só se todas as partes forem publicadas) e
  `drop_categories`. Aplicadas antes de renomear e recodificar, com testes.
- **Classificações harmonizadas** só da série (`c11558h`, `c67h`, com `datasets`), para
  não mexer nas classificações geradas.
- **Séries:** `esgotamento_serie`, `lixo_serie` e `alfabetizacao_serie`
  (`configs/indicators/demografia/compostas.toml`), cada uma com a nota de fontes
  distintas e as diferenças de 2022.
- **Portal:** cada ponto traz a tabela de origem (`source_table_id`). O gráfico de
  evolução marca a mudança de fonte com uma linha tracejada e legenda, e o tooltip diz
  a tabela do ponto.

