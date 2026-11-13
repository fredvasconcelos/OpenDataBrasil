# Série histórica do Censo Demográfico: inventário e decisões

Levantamento de 2026-11-13 (ADR-0021), feito com os descritores oficiais do SIDRA dos
temas de população e domicílios (663 tabelas, 410 do Censo). Os temas de educação,
trabalho e rendimento ainda não foram lidos.

## Estado por KPI do Censo 2022

| KPI (tabela-base) | Edições anteriores candidatas | Situação |
|---|---|---|
| População nos Censos (1286, 1872–2010) | 1209 (variável 606) traz 2022 | **feito** (gerado) |
| Densidade demográfica (4714, 2022) | 1298 (variável 614, 1872–2010, até UF) | limpa; KPI curado: próxima etapa |
| População por cor ou raça (9605, 2010 e 2022) | 136 (variável 93, 1991 e 2000) | limpa; Total com outro código (0 → 95251); "Sem declaração" só em 1991 e 2000; KPI curado: próxima etapa |
| População residente, por sexo e idade (9606) | 202 (sexo, 1970–2000); 200 (sexo e grupos de idade, 1970–2000) | sexo limpo; idade usa outra classificação (c58, grupos) e precisa de equivalência com os grupos quinquenais da c287 |
| Índice de envelhecimento (9515, 2022) | 9756 (variável 9175, 2010) | **para decidir:** em 2010 o índice usa 60 anos ou mais; confirmar se é o mesmo conceito da 9515 |
| Domicílios ocupados (4712, 2022) | 156 (2048 "domicílios particulares ocupados", 1991–2010) | **para decidir:** conceito diferente (inclui os improvisados) |
| Água, esgoto e lixo (6803, 6805, 6892, 2022) | 2000: 1437, 1439, 1453, 1454; 1991: 182; 2010: 3154, 2065 | **para decidir:** variável 96 ("permanentes", unidade "Unidades") × 381 ("permanentes ocupados", "Domicílios"), e as categorias das classificações mudaram. Exige equivalência curada, como na POF |
| Migrantes entre UFs (10159, 2022) | 2403 (2000, UF de residência 5 anos antes) | **para decidir:** mesmo quesito (data fixa), variável e classificação diferentes |
| Taxa de alfabetização (9543), nível de instrução (10061), rendimento domiciliar (10295) | não lidas (temas de educação e rendimento) | próximo levantamento |
| Indígenas, quilombolas, favelas | — | sem série: quilombolas são de 2022; favelas eram "aglomerados subnormais" em 2010, com outro critério |
| Taxa de crescimento (4709) | — | a taxa entre Censos pode ser derivada da 1286 (fórmula geométrica); fica como indicador derivado (§15.5), para decidir |

## Próximos passos

1. Ler os descritores dos temas de educação, trabalho e rendimento e completar a
   tabela acima.
2. Levar as edições limpas aos KPIs curados (1298, 136, 202), atualizando as fixtures.
3. Com as decisões do mantenedor, curar as equivalências de domicílios e saneamento.
