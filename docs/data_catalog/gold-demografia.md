# Gold do escopo `demografia`

Definição: [`configs/indicators/demografia.toml`](../../configs/indicators/demografia.toml)
(catálogo semântico 1.0.0). Modelo: [ADR-0008](../adr/0008-gold-modelo-hierarquico-e-camada-semantica.md).
Operação: [runbook da Gold](../runbooks/gold.md).

Primeiro release com dados reais: `22de665f-baa6-420d-96cd-1ea5f1daf4a9`
(2026-11-04), com 459.468 observações e 71 verificações aprovadas. Release
**interno**: a licença do IBGE ainda está em `requires_review` (KI-003).

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
  Pessoas quilombolas
    Pessoas quilombolas                                censo_pessoas_quilombolas              (9578/4709)
    População residente por localização                censo_residentes_territorio_quilombola (9578/93)
    Percentual de pessoas quilombolas                  censo_percentual_quilombolas           (9578/4728, não aditivo)
      Localização do domicílio: Em territórios quilombolas, Fora de territórios quilombolas
```

Todos os indicadores estão publicados nos níveis Brasil, Grande Região, UF e
município. Regiões geográficas intermediárias e imediatas existem na
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

Cada medida tem a coluna `<medida>_status`, com a legenda da Silver (`valid`,
`true_zero`, `suppressed`...) ou `absent` quando a combinação não foi publicada.

## Etapa 4b (aprovada, não implementada)

- 9970 e 9971: pessoas indígenas por sexo e idade. A 9971 cruza 4 classificações.
- 9954 e 9723: terras indígenas e territórios quilombolas como unidades
  territoriais. Os códigos de nível no SIDRA ainda precisam ser verificados,
  e o modelo pede um sistema territorial ligado aos municípios por relação
  muitos-para-muitos.
