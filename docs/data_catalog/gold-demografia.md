# Gold do escopo `demografia`

Definição: [`configs/indicators/demografia.toml`](../../configs/indicators/demografia.toml)
(catálogo semântico 1.3.0). Modelo: [ADR-0008](../adr/0008-gold-modelo-hierarquico-e-camada-semantica.md).
Operação: [runbook da Gold](../runbooks/gold.md).

Releases com dados reais (2026-11-04):

| Release | Conteúdo | Observações | Verificações |
|---|---|---|---|
| `22de665f-baa6-420d-96cd-1ea5f1daf4a9` (superseded) | Fase 4: 6579, 4714, 9605, 9718, 9578 | 459.468 | 71 aprovadas |
| `26826057-8dc5-4f36-86b8-6e6efa33e591` (superseded) | + etapa 4b: 9971, 9970 | 3.373.605 | 112 aprovadas |
| `963a5558-68d4-4881-ac41-4bd65008fb9a` (superseded) | + 9723 (territórios quilombolas e Amazônia Legal) | 3.393.438 | 115 aprovadas |
| `c9c90f26-6439-4559-9195-5c829472cee2` (**ativo**) | + 9954 (terras indígenas e Coordenações Regionais da Funai) | 3.891.210 | 127 aprovadas |

Release **interno**: a licença do IBGE ainda está em `requires_review` (KI-003).

## Árvore temática

```text
Estimativas de População
  População residente estimada                         populacao_estimada                     (6579/9324)
Censo Demográfico
  População
    População residente                                censo_populacao_residente              (4714/93)
  Território
    Área da unidade territorial                        censo_area_territorial                 (4714/6318)
    Densidade demográfica                              censo_densidade_demografica            (4714/614, não aditivo)
  Cor ou raça
    População residente por cor ou raça                censo_populacao_cor_raca               (9605/93)
      Cor ou raça: Branca, Preta, Amarela, Parda, Indígena
  Pessoas indígenas
    Pessoas indígenas                                  censo_pessoas_indigenas                (9718/350)
    População residente por quesito de declaração      censo_residentes_declaracao_indigena   (9718/93)
    Percentual de pessoas indígenas                    censo_percentual_indigenas             (9718/4727, não aditivo)
      Quesito de declaração indígena: Cor ou raça indígena, Se considera indígena, Não se declarou indígena
      Localização do domicílio: Em terras indígenas, Fora de terras indígenas
    Pessoas indígenas por sexo e grupo de idade        censo_pessoas_indigenas_sexo_idade     (9971/350)
      Sexo: Homens, Mulheres; Grupo de idade: 0 a 4 ... 85 anos ou mais; Localização; Situação: Urbana, Rural
    Pessoas indígenas por idade                        censo_pessoas_indigenas_idade          (9970/350; Brasil, Regiões, UFs)
      Idade: 21 grupos quinquenais › idades simples › meses de vida (menos de 1 ano); Localização; Situação
    Terras indígenas
      Pessoas residentes em terras indígenas            censo_residentes_terras_indigenas      (9954/576)
      Pessoas indígenas em terras indígenas             censo_indigenas_em_terras_indigenas    (9954/1432)
        Sexo; Idade (grupos quinquenais); Situação do domicílio
  Pessoas quilombolas
    Territórios quilombolas
      Pessoas residentes em territórios quilombolas     censo_residentes_territorios_quilombolas (9723/6559)
      Pessoas quilombolas em territórios quilombolas    censo_quilombolas_em_territorios       (9723/7079)
      Percentual de quilombolas nos territórios         censo_percentual_quilombolas_territorios (9723/7080, não aditivo)
    Pessoas quilombolas                                censo_pessoas_quilombolas              (9578/4709)
    População residente por localização                censo_residentes_territorio_quilombola (9578/93)
    Percentual de pessoas quilombolas                  censo_percentual_quilombolas           (9578/4728, não aditivo)
      Localização do domicílio: Em territórios quilombolas, Fora de territórios quilombolas
```

Os indicadores estão publicados nos níveis Brasil, Grande Região, UF e
município, exceto `censo_pessoas_indigenas_idade` (até UF). Os indicadores da
9723 também estão nos recortes especiais `territorio_quilombola` (495),
`territorio_quilombola_uf` (503), `amazonia_legal` e `amazonia_legal_uf`; os da
9954 em `terra_indigena` (573), `terra_indigena_uf` (602) e
`coordenacao_regional_funai` (39), sem o nível municipal
([níveis](ibge-niveis-territoriais.md)). Regiões geográficas intermediárias e imediatas existem na
hierarquia (para recortes e somas derivadas), mas não têm valores oficiais
publicados nestas tabelas.

## Regras semânticas

| Regra | Onde |
|---|---|
| Percentuais e densidade nunca são somados | `additivity = "non_additive"` |
| "Pessoas indígenas" (9718) e a categoria Indígena de cor ou raça (9605) não são combinadas | `incompatible_with` |
| Classificações não pedidas ficam no Total | planejador (`list_has_all`) |
| Totais de UF, Grande Região e Brasil são os oficiais, não a soma dos municípios | modelo; `--sum-to` marca o resultado como derivado |
| 2004, 2008 e 2012 (6579): a soma municipal inclui municípios com instalação prevista | `pending_installation` no fato e `flags` na observação |

## Fatos

| Fato | Granularidade | Medidas |
|---|---|---|
| `fact_population_estimate` | território × ano | `population`, `pending_installation` |
| `fact_census_population` | território × ano censitário | `population`, `area_km2`, `density` |
| `fact_population_by_race` | território × ano × cor ou raça | `population` |
| `fact_indigenous_population` | território × ano × quesito × localização | `population`, `indigenous_persons`, `indigenous_share_pct` |
| `fact_quilombola_population` | território × ano × localização | `population`, `quilombola_persons`, `quilombola_share_pct` |
| `fact_indigenous_by_sex_age` | território × ano × sexo × grupo de idade × localização × situação | `indigenous_persons` |
| `fact_indigenous_by_age` | território (até UF) × ano × idade × localização × situação | `indigenous_persons` |
| `fact_quilombola_territory` | território (inclusive recortes especiais) × ano | `residents`, `quilombola_persons`, `quilombola_share_pct` |
| `fact_indigenous_land` | território (inclusive terras indígenas) × ano × sexo × grupo de idade × situação | `residents`, `indigenous_persons` |

Cada medida tem a coluna `<medida>_status`, com a legenda da Silver (`valid`,
`true_zero`, `suppressed`...) ou `absent` quando a combinação não foi publicada.

## Etapa 4b

- **Concluído:** 9971 (sexo × grupos de idade × localização × situação, em todos
  os níveis) e 9970 (idade simples em 3 níveis de hierarquia, até UF).
- **Concluído:** 9723 (territórios quilombolas como recorte territorial
  próprio, com as partes por UF, e Amazônia Legal), com os códigos de nível
  informados pelo mantenedor e conferidos na API.
- **Concluído:** 9954 (terras indígenas, partes por UF e Coordenações Regionais
  da Funai), por sexo, grupos quinquenais de idade e situação do domicílio.
- **Derivados não publicados:** razão de sexo, 0 a 14 anos, 60 anos ou mais.
  Podem ser calculados a partir das categorias (exportação ou consulta), mas
  não são indicadores oficiais da plataforma.
