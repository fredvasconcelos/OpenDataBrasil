# Dicionários dos indicadores — revisão documental de 26/11/2026

**Integração em desenvolvimento local:** as fichas, apoios, códigos, fontes e métodos
obtidos passaram a compor a API documental e os metadados das exportações. A
[preparação das 50 candidatas](preparacao-expansao.json) confere configuração e
mantém seus impedimentos. Ver [contrato implementado](../../development/exportacao-rastreavel.md).
A integração preserva o estado de revisão parcial e não ativa dados ou publica a beta.

Inventário da configuração vigente: **291 KPIs e 334 indicadores semânticos**, em 335 fichas (uma por KPI e por indicador de apoio sem KPI). Dois KPIs usam o mesmo indicador semântico. A disponibilidade abaixo vem do snapshot da API do release `f1b77232-3f14-4e63-b943-82fed4fa2886`, confrontado com a configuração atual; **não é conferência ao vivo**.

**Estado: revisão parcial com inventário completo da configuração.** Todos têm lacunas metodológicas ou conceituais explícitas; nomes oficiais e links não são apresentados como definições completas.

- [Matriz de cobertura e lacunas](lacunas.csv) e [contagens verificadas](cobertura.json).
- [Candidatas N3/N4/N5](candidatas.csv): 50 KPIs separados do snapshot N2, com estado histórico e impedimentos próprios.
- [Fichas estruturadas](fichas.json), [ligações tabela/variável/edição](ligacoes.json), [campos](campos.csv) e [códigos/categorias](codigos.csv).
- [Sínteses de pesquisa e fontes](pesquisas.md), [IPCA e POF](ipca-pof.md) e [proposta Excel](../../development/especificacao-excel-rastreavel.md).
- [Contas públicas](contas.md): escopo próprio, sem acrescentar seus montantes aos KPIs estatísticos.
- [Códigos e base legal das contas](codigos-contas.md), [matriz por domínio/exercício](cobertura-codigos-contas.csv) e [caso 0A53](acao-0A53.md): 26 domínios inventariados, 13 verbetes confirmados; catálogo completo e enquadramento do recebimento pendentes.
- [Exemplo de códigos e normas](exemplo-codigos-normas.json) e [schema complementar](codigos-normas.schema.json): demonstração documental sem dados financeiros; não é novo exportador.

A ausência do campo Descricao não foi preenchida com o nome ou com uma interpretação inventada. As sínteses são explicações do Open Data Brasil; as fontes oficiais estão identificadas. Categorias oficiais não comprovam interseção disponível. Licenças dos dados continuam as dos produtores.

## Disponíveis no snapshot (241)

| Ficha | Indicador semântico | Unidade | Método |
|---|---|---|---|
| [Abate de bovinos](fichas/abate_bovinos.md) | `abate_bovinos` | Cabeças | M12 |
| [Horas dedicadas a afazeres domésticos e cuidados](fichas/afazeres_domesticos.md) | `afazeres_domesticos` | Horas | M05 |
| [Comercialização de agrotóxicos](fichas/agrotoxicos.md) | `agrotoxicos` | Toneladas | M42 |
| [Aleitamento materno exclusivo (menos de 6 meses)](fichas/aleitamento_exclusivo.md) | `aleitamento_exclusivo` | Mil pessoas | M06 |
| [Aleitamento materno exclusivo (%)](fichas/aleitamento_exclusivo_v7179.md) | `aleitamento_exclusivo_v7179` | % | M06 |
| [Taxa de alfabetização (Censos e PNAD)](fichas/alfabetizacao_serie.md) | `alfabetizacao_serie` | % | M01, M05 |
| [Média de anos de estudo (15 anos ou mais)](fichas/anos_estudo.md) | `anos_estudo` | Anos | M05 |
| [Produção de camarão (aquicultura)](fichas/aquicultura_camarao.md) | `aquicultura_camarao` | Quilogramas | M11 |
| [Produção de ostras, vieiras e mexilhões (aquicultura)](fichas/aquicultura_moluscos.md) | `aquicultura_moluscos` | Quilogramas | M11 |
| [Produção de peixes (aquicultura)](fichas/aquicultura_peixes.md) | `aquicultura_peixes` | Quilogramas | M11 |
| [Valor da produção da aquicultura](fichas/aquicultura_valor.md) | `aquicultura_valor` | Mil Reais | M11 |
| [Aquisição alimentar domiciliar per capita](fichas/aquisicao_alimentar.md) | `aquisicao_alimentar` | Quilogramas | M08 |
| [Área colhida das lavouras](fichas/area_colhida_lavouras.md) | `area_colhida_lavouras` | Hectares | M09 |
| [Área territorial de favelas](fichas/area_favelas.md) | `area_favelas` | Quilômetros quadrados | M01 |
| [Área florestal em proporção do território](fichas/area_florestal.md) | `area_florestal` | % | M50 |
| [Área de silvicultura por espécie florestal](fichas/area_silvicultura.md) | `area_silvicultura` | Hectares | M15 |
| [Domicílios por tipo de arranjo (unidade doméstica)](fichas/arranjos_domiciliares.md) | `arranjos_domiciliares` | Mil unidades | M05 |
| [Volume das atividades turísticas](fichas/atividades_turisticas.md) | `atividades_turisticas` | Número-índice | M23 |
| [Avaliação do próprio estado de saúde](fichas/autoavaliacao_saude.md) | `autoavaliacao_saude` | Mil pessoas | M06 |
| [Casamentos](fichas/casamentos.md) | `casamentos` | Unidades | M04 |
| [Casamentos por mês](fichas/casamentos_mensal.md) | `casamentos_mensal` | Unidades | M04 |
| [Pessoas com celular para uso pessoal](fichas/celular_uso_pessoal.md) | `celular_uso_pessoal` | Mil pessoas | M05 |
| [Área territorial](fichas/area_territorial.md) | `censo_area_territorial` | Quilômetros quadrados | M01 |
| [Densidade demográfica](fichas/densidade_demografica.md) | `censo_densidade_demografica` | Habitante por quilômetro quadrado | M01 |
| [Pessoas indígenas em terras indígenas](fichas/indigenas_em_terras_indigenas.md) | `censo_indigenas_em_terras_indigenas` | Pessoas | M01 |
| [Percentual de pessoas indígenas](fichas/percentual_indigenas.md) | `censo_percentual_indigenas` | % | M01 |
| [Percentual de pessoas quilombolas](fichas/percentual_quilombolas.md) | `censo_percentual_quilombolas` | % | M01 |
| [Pessoas indígenas](fichas/pessoas_indigenas.md) | `censo_pessoas_indigenas_sexo_idade` | Pessoas | M01 |
| [Pessoas quilombolas](fichas/pessoas_quilombolas.md) | `censo_pessoas_quilombolas_sexo` | Pessoas | M01 |
| [População por cor ou raça (2010 e 2022)](fichas/populacao_cor_raca_censos.md) | `censo_populacao_cor_raca` | Pessoas | M01 |
| [População residente (Censo)](fichas/populacao_residente.md) | `censo_populacao_cor_raca_sexo` | Pessoas | M01 |
| [População por sexo e idade](fichas/populacao_sexo_idade.md) | `censo_populacao_cor_raca_sexo` | Pessoas | M01 |
| [Pessoas quilombolas em territórios quilombolas](fichas/quilombolas_em_territorios.md) | `censo_quilombolas_em_territorios_sexo` | Pessoas | M01 |
| [Pessoas residentes em terras indígenas](fichas/residentes_em_terras_indigenas.md) | `censo_residentes_terras_indigenas` | Pessoas | M01 |
| [Pessoas residentes em territórios quilombolas](fichas/residentes_em_territorios_quilombolas.md) | `censo_residentes_territorios_quilombolas_sexo` | Pessoas | M01 |
| [Domicílios próprios, alugados e cedidos](fichas/condicao_ocupacao.md) | `condicao_ocupacao` | Mil unidades | M05 |
| [Municípios com conselhos municipais nas áreas sociais](fichas/conselhos_municipais_sociais.md) | `conselhos_municipais_sociais` | Unidades | M35 |
| [Consultaram médico nos últimos 12 meses](fichas/consulta_medica.md) | `consulta_medica` | Mil pessoas | M06 |
| [Consultaram médico nos últimos 12 meses (%)](fichas/consulta_medica_v5362.md) | `consulta_medica_v5362` | % | M06 |
| [Consumo abusivo de álcool](fichas/consumo_abusivo_alcool.md) | `consumo_abusivo_alcool` | Mil pessoas | M06 |
| [Consumo abusivo de álcool (%)](fichas/consumo_abusivo_alcool_v4301.md) | `consumo_abusivo_alcool_v4301` | % | M06 |
| [Taxa de crescimento da população](fichas/crescimento_populacional.md) | `crescimento_populacional` | % | M01 |
| [Custo médio do metro quadrado da construção](fichas/custo_m2.md) | `custo_m2` | Reais | M24 |
| [Densidade demográfica em favelas](fichas/densidade_favelas.md) | `densidade_favelas` | Habitante por quilômetro quadrado | M01 |
| [Desflorestamento na Amazônia Legal](fichas/desflorestamento_amazonia.md) | `desflorestamento_amazonia` | Quilômetros quadrados | M41 |
| [Despesa média mensal familiar](fichas/despesa_familiar.md) | `despesa_familiar` | Reais | M08 |
| [Domicílios por destino do lixo (Censo)](fichas/destino_lixo_censo.md) | `destino_lixo_censo` | Unidades | M01 |
| [Domicílios por destino do lixo](fichas/destino_lixo_pnad.md) | `destino_lixo_pnad` | Mil unidades | M05 |
| [Diagnóstico de diabetes](fichas/diabetes.md) | `diabetes` | Mil pessoas | M06 |
| [Diagnóstico de diabetes (%)](fichas/diabetes_v4465.md) | `diabetes_v4465` | % | M06 |
| [Divórcios](fichas/divorcios.md) | `divorcios` | Unidades | M04 |
| [Pessoas com pelo menos uma doença crônica](fichas/doenca_cronica.md) | `doenca_cronica` | Mil pessoas | M06 |
| [Pessoas com pelo menos uma doença crônica (%)](fichas/doenca_cronica_v11220.md) | `doenca_cronica_v11220` | % | M06 |
| [Domicílios com utilização da internet](fichas/domicilios_internet.md) | `domicilios_internet` | Mil unidades | M05 |
| [Domicílios particulares permanentes ocupados](fichas/domicilios_ocupados.md) | `domicilios_ocupados` | Domicílios | M01 |
| [Domicílios com televisão](fichas/domicilios_televisao.md) | `domicilios_televisao` | Mil unidades | M05 |
| [Efetivo de rebanhos](fichas/efetivo_rebanhos.md) | `efetivo_rebanhos` | Cabeças | M11 |
| [Emprego na indústria em proporção do emprego total](fichas/emprego_industria.md) | `emprego_industria` | % | M33 |
| [Resultados das empresas comerciais](fichas/empresas_comerciais.md) | `empresas_comerciais` | Mil Reais | M20 |
| [Empresas de construção: pessoal, salários e valor das obras](fichas/empresas_construcao.md) | `empresas_construcao` | Unidades | M19 |
| [Empresas, pessoal ocupado e salários](fichas/empresas_emprego_formal.md) | `empresas_emprego_formal` | Unidades | M25 |
| [Salário médio mensal em reais](fichas/empresas_emprego_formal_v10143.md) | `empresas_emprego_formal_v10143` | Reais | M25 |
| [Número de empresas e outras organizações atuantes](fichas/empresas_emprego_formal_v367.md) | `empresas_emprego_formal_v367` | Unidades | M25 |
| [Salários e outras remunerações](fichas/empresas_emprego_formal_v662.md) | `empresas_emprego_formal_v662` | Mil Reais | M25 |
| [Pessoal ocupado total](fichas/empresas_emprego_formal_v707.md) | `empresas_emprego_formal_v707` | Pessoas | M25 |
| [Pessoal ocupado assalariado](fichas/empresas_emprego_formal_v708.md) | `empresas_emprego_formal_v708` | Pessoas | M25 |
| [Empresas que implementaram inovações](fichas/empresas_inovadoras.md) | `empresas_inovadoras` | Unidades | M28 |
| [Energias renováveis na oferta interna de energia](fichas/energia_renovavel.md) | `energia_renovavel` | % | M45 |
| [Índice de envelhecimento](fichas/envelhecimento.md) | `envelhecimento` | Razão | M01 |
| [Escolares de 13 a 17 anos que consumiram bebida alcoólica](fichas/escolares_alcool.md) | `escolares_alcool` | % | M07 |
| [Escolares de 13 a 17 anos com excesso de peso](fichas/escolares_excesso_peso.md) | `escolares_excesso_peso` | % | M07 |
| [Escolares de 13 a 17 anos que fumaram nos últimos 30 dias](fichas/escolares_fumaram.md) | `escolares_fumaram` | % | M07 |
| [Domicílios por tipo de esgotamento sanitário (Censo)](fichas/esgotamento_censo.md) | `esgotamento_censo` | Unidades | M01 |
| [Domicílios por tipo de esgotamento sanitário](fichas/esgotamento_pnad.md) | `esgotamento_pnad` | Mil unidades | M05 |
| [Esgotamento sanitário (PNAD e Censo)](fichas/esgotamento_serie.md) | `esgotamento_serie` | Unidades | M01, M05 |
| [Águas residuais domésticas tratadas de forma segura](fichas/esgoto_tratado.md) | `esgoto_tratado` | % | M44 |
| [Esperança de vida ao nascer (projeção para 2026)](fichas/esperanca_vida.md) | `esperanca_vida` | Anos | M03 |
| [Número e área dos estabelecimentos agropecuários](fichas/estabelecimentos_area.md) | `estabelecimentos_area` | Unidades | M16 |
| [Área dos estabelecimentos agropecuários](fichas/estabelecimentos_area_v184.md) | `estabelecimentos_area_v184` | Hectares | M16 |
| [Estabelecimentos de saúde](fichas/estabelecimentos_saude.md) | `estabelecimentos_saude` | Unidades | M37 |
| [Estabelecimentos agropecuários (série histórica 1920–2006)](fichas/estabelecimentos_serie.md) | `estabelecimentos_serie` | Unidades | M16 |
| [Nível de estresse hídrico](fichas/estresse_hidrico.md) | `estresse_hidrico` | % | M44 |
| [Excesso de peso ou obesidade](fichas/excesso_peso.md) | `excesso_peso` | Mil pessoas | M06 |
| [Excesso de peso em adultos (%)](fichas/excesso_peso_v11675.md) | `excesso_peso_v11675` | % | M06 |
| [Valor das exportações (2013–2015)](fichas/exportacoes_importacoes.md) | `exportacoes_importacoes` | Mil dólares FOB | M49 |
| [Valor das importações (2013–2015)](fichas/exportacoes_importacoes_v2152.md) | `exportacoes_importacoes_v2152` | Mil dólares FOB | M49 |
| [Saldo comercial (2013–2015)](fichas/exportacoes_importacoes_v2154.md) | `exportacoes_importacoes_v2154` | Mil dólares FOB | M49 |
| [Taxa de fecundidade total](fichas/fecundidade_total.md) | `fecundidade_total` | Filhos | M03 |
| [Fertilizantes entregues ao consumidor final](fichas/fertilizantes.md) | `fertilizantes` | Toneladas | M48 |
| [Focos de calor por bioma](fichas/focos_calor.md) | `focos_calor` | Unidades | M40 |
| [Principal fonte de abastecimento de água](fichas/fonte_abastecimento.md) | `fonte_abastecimento` | Mil unidades | M05 |
| [Força de trabalho, ocupação e desocupação](fichas/forca_trabalho.md) | `forca_trabalho` | Mil pessoas | M05 |
| [Pessoas de 14 anos ou mais de idade](fichas/forca_trabalho_v1641.md) | `forca_trabalho_v1641` | Mil pessoas | M05 |
| [Pessoas de 14 anos ou mais de idade, na força de trabalho, na semana de referência](fichas/forca_trabalho_v4088.md) | `forca_trabalho_v4088` | Mil pessoas | M05 |
| [Pessoas de 14 anos ou mais de idade, desocupadas na semana de referência](fichas/forca_trabalho_v4092.md) | `forca_trabalho_v4092` | Mil pessoas | M05 |
| [Pessoas de 14 anos ou mais de idade, fora da força de trabalho, na semana de referência](fichas/forca_trabalho_v4094.md) | `forca_trabalho_v4094` | Mil pessoas | M05 |
| [Taxa de participação na força de trabalho, na semana de referência, das pessoas de 14 anos ou mais de idade](fichas/forca_trabalho_v4096.md) | `forca_trabalho_v4096` | % | M05 |
| [Taxa de desocupação, na semana de referência, das pessoas de 14 anos ou mais de idade](fichas/forca_trabalho_v4099.md) | `forca_trabalho_v4099` | % | M05 |
| [Frequência escolar líquida no ensino fundamental](fichas/frequencia_liquida.md) | `frequencia_liquida` | % | M05 |
| [Fumantes atuais de tabaco](fichas/fumantes.md) | `fumantes` | Mil pessoas | M06 |
| [Fumantes atuais de tabaco (%)](fichas/fumantes_v4163.md) | `fumantes_v4163` | % | M06 |
| [Índice de Gini do rendimento domiciliar per capita](fichas/gini_domiciliar.md) | `gini_domiciliar` | Índice | M05 |
| [Diagnóstico de hipertensão arterial](fichas/hipertensao.md) | `hipertensao` | Mil pessoas | M06 |
| [Diagnóstico de hipertensão arterial (%)](fichas/hipertensao_v4399.md) | `hipertensao_v4399` | % | M06 |
| [Vítimas de homicídio por 100 mil habitantes](fichas/homicidios.md) | `homicidios` | Óbitos por 100 mil habitantes | M47 |
| [Vítimas de homicídios intencionais (ODS)](fichas/homicidios_v13533.md) | `homicidios_v13533` | Óbitos | M47 |
| [População de referência dos homicídios (ODS)](fichas/homicidios_v606.md) | `homicidios_v606` | Pessoas | M47 |
| [Idade mediana (Censo)](fichas/idade_mediana.md) | `idade_mediana` | Anos | M01 |
| [Unidades locais industriais, pessoal ocupado e salários](fichas/industria_uf.md) | `industria_uf` | Unidades | M18 |
| [INPC](fichas/inpc.md) | `inpc` | % | M30 |
| [Pessoas insuficientemente ativas](fichas/insuficientemente_ativos.md) | `insuficientemente_ativos` | Mil pessoas | M06 |
| [Pessoas insuficientemente ativas (%)](fichas/insuficientemente_ativos_v4265.md) | `insuficientemente_ativos_v4265` | % | M06 |
| [Produção de insumos típicos da construção civil](fichas/insumos_construcao.md) | `insumos_construcao` | Número-índice | M17 |
| [IPCA](fichas/ipca.md) | `ipca` | % | M29 |
| [IPCA-15](fichas/ipca15.md) | `ipca15` | % | M31 |
| [Índice de Preços ao Produtor](fichas/ipp.md) | `ipp` | % | M32 |
| [Municípios com legislação ambiental](fichas/legislacao_ambiental.md) | `legislacao_ambiental` | Unidades | M35 |
| [Leite adquirido e industrializado](fichas/leite_adquirido.md) | `leite_adquirido` | Mil litros | M13 |
| [Destino do lixo (PNAD e Censo)](fichas/lixo_serie.md) | `lixo_serie` | Unidades | M01, M05 |
| [Massa de rendimento real do trabalho](fichas/massa_rendimento.md) | `massa_rendimento` | Milhões de Reais | M05 |
| [Massa de rendimento mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, efetivamente recebido em todos os trabalhos](fichas/massa_rendimento_v6295.md) | `massa_rendimento_v6295` | Milhões de Reais | M05 |
| [Domicílios por material das paredes](fichas/material_paredes.md) | `material_paredes` | Mil unidades | M05 |
| [Média de moradores por domicílio](fichas/media_moradores_domicilio.md) | `media_moradores_domicilio` | Pessoas | M01 |
| [Microempreendedores individuais (MEI)](fichas/microempreendedores.md) | `microempreendedores` | Unidades | M26 |
| [Número de microempreendedores individuais (MEIs) (entrada)](fichas/microempreendedores_v8890.md) | `microempreendedores_v8890` | Unidades | M26 |
| [Taxa de entrada de microempreendedores individuais (MEIs)](fichas/microempreendedores_v8891.md) | `microempreendedores_v8891` | % | M26 |
| [Número de microempreendedores individuais (MEIs) (saída)](fichas/microempreendedores_v8892.md) | `microempreendedores_v8892` | Unidades | M26 |
| [Taxa de saída de microempreendedores individuais (MEIs)](fichas/microempreendedores_v8893.md) | `microempreendedores_v8893` | % | M26 |
| [Número de microempreendedores individuais (MEIs) (saldo)](fichas/microempreendedores_v8894.md) | `microempreendedores_v8894` | Unidades | M26 |
| [Pessoas que não residiam na UF cinco anos antes](fichas/migrantes_uf.md) | `migrantes_uf` | Pessoas | M01 |
| [Moradores em domicílios ocupados](fichas/moradores_domicilios_ocupados.md) | `moradores_domicilios_ocupados` | Pessoas | M01 |
| [Mortalidade por doenças crônicas não transmissíveis](fichas/mortalidade_doencas_cronicas.md) | `mortalidade_doencas_cronicas` | Porcentagem | M47 |
| [Óbitos por doenças crônicas (30 a 69 anos)](fichas/mortalidade_doencas_cronicas_v12948.md) | `mortalidade_doencas_cronicas_v12948` | Óbitos | M47 |
| [População de 30 a 69 anos (ODS)](fichas/mortalidade_doencas_cronicas_v93.md) | `mortalidade_doencas_cronicas_v93` | Número de pessoas | M47 |
| [Razão de mortalidade materna](fichas/mortalidade_materna.md) | `mortalidade_materna` | Óbitos por 100 mil nascidos vivos | M47 |
| [Óbitos maternos (ODS)](fichas/mortalidade_materna_v9435.md) | `mortalidade_materna_v9435` | Pessoas | M47 |
| [Nascidos vivos de mães residentes (ODS)](fichas/mortalidade_materna_v9436.md) | `mortalidade_materna_v9436` | Pessoas | M47 |
| [Taxa de mortalidade em menores de 5 anos](fichas/mortalidade_menores_5.md) | `mortalidade_menores_5` | Óbitos por mil nascidos vivos | M47 |
| [Nascidos vivos](fichas/nascidos_vivos.md) | `nascidos_vivos` | Pessoas | M04 |
| [Nascimentos de empresas e taxa de sobrevivência](fichas/nascimentos_empresas.md) | `nascimentos_empresas` | Unidades | M27 |
| [Pessoas de 25 anos ou mais por nível de instrução](fichas/nivel_instrucao.md) | `nivel_instrucao` | Mil pessoas | M05 |
| [Nível de instrução em quatro grupos (PNAD)](fichas/nivel_instrucao_capitais.md) | `nivel_instrucao_capitais` | Mil pessoas | M05 |
| [Nível de instrução (18 anos ou mais, Censo)](fichas/nivel_instrucao_censo.md) | `nivel_instrucao_censo` | Pessoas | M01 |
| [Número de favelas e comunidades urbanas](fichas/numero_favelas.md) | `numero_favelas` | Unidades | M01 |
| [Óbitos](fichas/obitos.md) | `obitos` | Pessoas | M04 |
| [Óbitos por mês](fichas/obitos_mensal.md) | `obitos_mensal` | Pessoas | M04 |
| [Ovinos tosquiados](fichas/ovinos_tosquiados.md) | `ovinos_tosquiados` | Cabeças | M11 |
| [Produção de ovos de galinha](fichas/ovos_produzidos.md) | `ovos_produzidos` | Mil dúzias | M14 |
| [Dispêndio em P&D em proporção do PIB](fichas/pd_pib.md) | `pd_pib` | % | M46 |
| [Pessoas que utilizaram a internet](fichas/pessoas_internet.md) | `pessoas_internet` | Mil pessoas | M05 |
| [PIB dos municípios e valor adicionado por atividade](fichas/pib_municipios.md) | `pib_municipios` | Mil Reais | M34 |
| [Valor adicionado bruto a preços correntes total](fichas/pib_municipios_v498.md) | `pib_municipios_v498` | Mil Reais | M34 |
| [Valor adicionado bruto a preços correntes da agropecuária](fichas/pib_municipios_v513.md) | `pib_municipios_v513` | Mil Reais | M34 |
| [Participação do valor adicionado bruto a preços correntes da agropecuária no valor adicionado bruto a preços correntes total](fichas/pib_municipios_v516.md) | `pib_municipios_v516` | % | M34 |
| [Valor adicionado bruto a preços correntes da administração, defesa, educação e saúde públicas e seguridade social](fichas/pib_municipios_v525.md) | `pib_municipios_v525` | Mil Reais | M34 |
| [Impostos, líquidos de subsídios, sobre produtos a preços correntes](fichas/pib_municipios_v543.md) | `pib_municipios_v543` | Mil Reais | M34 |
| [Valor adicionado bruto a preços correntes dos serviços, exclusive administração, defesa, educação e saúde públicas e seguridade social](fichas/pib_municipios_v6575.md) | `pib_municipios_v6575` | Mil Reais | M34 |
| [PIB a preços correntes](fichas/pib_per_capita.md) | `pib_per_capita` | Milhões de Reais | M33 |
| [População de referência das Contas Nacionais](fichas/pib_per_capita_v93.md) | `pib_per_capita_v93` | Mil pessoas | M33 |
| [PIB: variação anual em volume](fichas/pib_per_capita_v9810.md) | `pib_per_capita_v9810` | % | M33 |
| [Deflator do PIB: variação anual](fichas/pib_per_capita_v9811.md) | `pib_per_capita_v9811` | % | M33 |
| [PIB per capita a preços correntes](fichas/pib_per_capita_v9812.md) | `pib_per_capita_v9812` | Reais | M33 |
| [PIB trimestral a preços correntes](fichas/pib_trimestral.md) | `pib_trimestral` | Milhões de Reais | M33 |
| [Municípios com Plano Diretor](fichas/plano_diretor.md) | `plano_diretor` | Unidades | M35 |
| [Pessoas com plano de saúde](fichas/plano_saude.md) | `plano_saude` | Mil pessoas | M06 |
| [Pessoas com plano de saúde (%)](fichas/plano_saude_v5264.md) | `plano_saude_v5264` | % | M06 |
| [Municípios atingidos pela seca e com plano de contingência](fichas/plano_seca.md) | `plano_seca` | Unidades | M35 |
| [Municípios com planos municipais nas áreas sociais](fichas/planos_municipais_sociais.md) | `planos_municipais_sociais` | Unidades | M35 |
| [Proporção da população abaixo da linha de pobreza nacional](fichas/pobreza_linha_nacional.md) | `pobreza_linha_nacional` | Proporção (%) | pendente |
| [Despesa com alimentação por tipo (POF 1987 e 1995)](fichas/pof_despesa_alimentacao_antiga.md) | `pof_despesa_alimentacao_antiga` | % | M08 |
| [Distribuição da despesa familiar (POF 1987 e 1995)](fichas/pof_despesa_distribuicao_antiga.md) | `pof_despesa_distribuicao_antiga` | % | M08 |
| [Distribuição do recebimento familiar (POF 1987 e 1995)](fichas/pof_recebimento_distribuicao_antiga.md) | `pof_recebimento_distribuicao_antiga` | % | M08 |
| [População estimada](fichas/populacao_estimada.md) | `populacao_estimada` | Pessoas | M02 |
| [População residente em favelas](fichas/populacao_favelas.md) | `populacao_favelas` | Pessoas | M01 |
| [População nos Censos (série histórica)](fichas/populacao_nos_censos.md) | `populacao_nos_censos` | Pessoas | M01 |
| [Domicílios por posse de bens](fichas/posse_bens.md) | `posse_bens` | Mil unidades | M05 |
| [Mulheres que realizaram pré-natal](fichas/pre_natal.md) | `pre_natal` | Mil pessoas | M06 |
| [Mulheres que realizaram pré-natal (%)](fichas/pre_natal_v6639.md) | `pre_natal_v6639` | % | M06 |
| [Produção física industrial](fichas/producao_fisica.md) | `producao_fisica` | Número-índice | M17 |
| [Área plantada ou destinada à colheita](fichas/producao_lavouras.md) | `producao_lavouras` | Hectares | M09 |
| [Produção de mel, lã e casulos (PPM)](fichas/producao_mel_la_casulos.md) | `producao_mel_la_casulos` | Quilogramas | M11 |
| [Produção de leite (PPM)](fichas/producao_origem_animal.md) | `producao_origem_animal` | Mil litros | M11 |
| [Produção de ovos (PPM)](fichas/producao_ovos.md) | `producao_ovos` | Mil dúzias | M11 |
| [Razão de sexo (Censo)](fichas/razao_sexo.md) | `razao_sexo` | Razão | M01 |
| [Domicílios ligados à rede geral de água (Censo)](fichas/rede_geral_agua.md) | `rede_geral_agua` | Unidades | M01 |
| [Rendimento domiciliar per capita (Censo)](fichas/rendimento_domiciliar_censo.md) | `rendimento_domiciliar_censo` | Reais | M01 |
| [Valor do rendimento nominal mediano mensal domiciliar per capita dos moradores em domicílios particulares permanentes ocupados, exclusive os cuja condição no domicílio era pensionista, empregado(a) doméstico(a) ou parente do(a) empregado(a) doméstico(a)](fichas/rendimento_domiciliar_censo_v13534.md) | `rendimento_domiciliar_censo_v13534` | Reais | M01 |
| [Moradores em domicílios particulares permanentes ocupados, exclusive os cuja condição no domicílio era pensionista, empregado(a) doméstico(a) ou parente do(a) empregado(a) doméstico(a)](fichas/rendimento_domiciliar_censo_v13604.md) | `rendimento_domiciliar_censo_v13604` | Pessoas | M01 |
| [Rendimento médio mensal familiar](fichas/rendimento_familiar.md) | `rendimento_familiar` | Reais | M08 |
| [Rendimento médio real do trabalho](fichas/rendimento_medio_trabalho.md) | `rendimento_medio_trabalho` | Reais | M05 |
| [Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, habitualmente recebido em todos os trabalhos](fichas/rendimento_medio_trabalho_v5933.md) | `rendimento_medio_trabalho_v5933` | Reais | M05 |
| [Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, efetivamente recebido no trabalho principal](fichas/rendimento_medio_trabalho_v5934.md) | `rendimento_medio_trabalho_v5934` | Reais | M05 |
| [Rendimento médio mensal real das pessoas de 14 anos ou mais de idade ocupadas na semana de referência com rendimento de trabalho, efetivamente recebido em todos os trabalhos](fichas/rendimento_medio_trabalho_v5935.md) | `rendimento_medio_trabalho_v5935` | Reais | M05 |
| [Estimativa da safra (área, produção e rendimento)](fichas/safra_estimada.md) | `safra_estimada` | Hectares | M10 |
| [Domicílios por situação de segurança alimentar](fichas/seguranca_alimentar.md) | `seguranca_alimentar` | Mil unidades | M05 |
| [Moradores por situação de segurança alimentar](fichas/seguranca_alimentar_v10114.md) | `seguranca_alimentar_v10114` | Mil pessoas | M05 |
| [Distribuição dos moradores por segurança alimentar (%)](fichas/seguranca_alimentar_v10117.md) | `seguranca_alimentar_v10117` | % | M05 |
| [Distribuição dos domicílios por segurança alimentar (%)](fichas/seguranca_alimentar_v9784.md) | `seguranca_alimentar_v9784` | % | M05 |
| [Pessoas que se sentem seguras ao andar sozinhas perto de casa](fichas/sensacao_seguranca.md) | `sensacao_seguranca` | Mil pessoas | M05 |
| [Municípios com serviço de abastecimento por rede geral](fichas/servico_agua_municipios.md) | `servico_agua_municipios` | Unidades | M36 |
| [Municípios com rede coletora de esgoto](fichas/servico_esgoto_municipios.md) | `servico_esgoto_municipios` | Unidades | M36 |
| [Resultados dos serviços empresariais não financeiros](fichas/servicos_nao_financeiros.md) | `servicos_nao_financeiros` | Mil Reais | M21 |
| [Óbitos por residência (SIM)](fichas/sim_obitos_residencia.md) | `sim_obitos_residencia` | Óbitos | M38 |
| [Vítimas de estupro (registros policiais)](fichas/sinesp_estupro.md) | `sinesp_estupro` | Vítimas | M39 |
| [Vítimas de feminicídio (registros policiais)](fichas/sinesp_feminicidio.md) | `sinesp_feminicidio` | Vítimas | M39 |
| [Vítimas de homicídio doloso (registros policiais)](fichas/sinesp_homicidio_doloso.md) | `sinesp_homicidio_doloso` | Vítimas | M39 |
| [Vítimas de latrocínio (roubo seguido de morte)](fichas/sinesp_latrocinio.md) | `sinesp_latrocinio` | Vítimas | M39 |
| [Mortes por intervenção de agente do Estado](fichas/sinesp_morte_intervencao.md) | `sinesp_morte_intervencao` | Vítimas | M39 |
| [Roubos de veículo (registros policiais)](fichas/sinesp_roubo_veiculo.md) | `sinesp_roubo_veiculo` | Ocorrências | M39 |
| [Taxa de alfabetização (15 anos ou mais, Censo)](fichas/taxa_alfabetizacao_censo.md) | `taxa_alfabetizacao_censo` | % | M01 |
| [Taxa de analfabetismo (15 anos ou mais)](fichas/taxa_analfabetismo.md) | `taxa_analfabetismo` | % | M05 |
| [Taxa de escolarização](fichas/taxa_escolarizacao.md) | `taxa_escolarizacao` | % | M05 |
| [Taxa de informalidade](fichas/taxa_informalidade.md) | `taxa_informalidade` | % | M05 |
| [Taxa de informalidade (trimestral)](fichas/taxa_informalidade_trimestral.md) | `taxa_informalidade_trimestral` | % | M05 |
| [Taxa de investimento](fichas/taxa_investimento.md) | `taxa_investimento` | % | M33 |
| [Taxa de poupança](fichas/taxa_poupanca.md) | `taxa_poupanca` | % | M33 |
| [Taxas de desocupação e de subutilização](fichas/taxas_desocupacao.md) | `taxas_desocupacao` | % | M05 |
| [Taxa combinada de desocupação e de subocupação por insuficiência de horas trabalhadas, na semana de referência, das pessoas de 14 anos ou mais de idade](fichas/taxas_desocupacao_v4114.md) | `taxas_desocupacao_v4114` | % | M05 |
| [Taxa combinada de desocupação e força de trabalho potencial, na semana de referência, das pessoas de 14 anos ou mais de idade](fichas/taxas_desocupacao_v4116.md) | `taxas_desocupacao_v4116` | % | M05 |
| [Taxa composta de subutilização da força de trabalho, na semana de referência, das pessoas de 14 anos ou mais de idade](fichas/taxas_desocupacao_v4118.md) | `taxas_desocupacao_v4118` | % | M05 |
| [Pessoas que tiveram ou consideram que tiveram COVID-19](fichas/tiveram_covid.md) | `tiveram_covid` | Mil pessoas | M05 |
| [Pessoas que tiveram COVID-19 (%)](fichas/tiveram_covid_v9448.md) | `tiveram_covid_v9448` | % | M05 |
| [Pessoas de 5 a 17 anos em trabalho infantil](fichas/trabalho_infantil.md) | `trabalho_infantil` | % | M05 |
| [Unidades de conservação terrestres](fichas/unidades_conservacao.md) | `unidades_conservacao` | Unidades | M43 |
| [Valor adicionado da indústria em proporção do PIB](fichas/va_industria_pib.md) | `va_industria_pib` | % | M33 |
| [Vacas ordenhadas](fichas/vacas_ordenhadas.md) | `vacas_ordenhadas` | Cabeças | M11 |
| [Vacinados contra a COVID-19](fichas/vacinacao_covid.md) | `vacinacao_covid` | Mil pessoas | M05 |
| [Vacinação contra a COVID-19 (%)](fichas/vacinacao_covid_v9004.md) | `vacinacao_covid_v9004` | % | M05 |
| [Valor da produção de origem animal](fichas/valor_producao_animal.md) | `valor_producao_animal` | Mil Reais | M11 |
| [Valor da produção das lavouras](fichas/valor_producao_lavouras.md) | `valor_producao_lavouras` | Mil Reais | M09 |
| [PIB: variação contra o mesmo trimestre do ano anterior](fichas/variacao_pib_trimestral.md) | `variacao_pib_trimestral` | % | M33 |
| [PIB: variação acumulada em quatro trimestres](fichas/variacao_pib_trimestral_v6562.md) | `variacao_pib_trimestral_v6562` | % | M33 |
| [PIB: variação acumulada no ano](fichas/variacao_pib_trimestral_v6563.md) | `variacao_pib_trimestral_v6563` | % | M33 |
| [PIB: variação contra o trimestre anterior](fichas/variacao_pib_trimestral_v6564.md) | `variacao_pib_trimestral_v6564` | % | M33 |
| [Volume de vendas de materiais de construção](fichas/vendas_materiais.md) | `vendas_materiais` | Número-índice | M22 |
| [Volume de vendas no varejo](fichas/vendas_varejo.md) | `vendas_varejo` | Número-índice | M22 |
| [Volume de vendas no varejo ampliado](fichas/vendas_varejo_ampliado.md) | `vendas_varejo_ampliado` | Número-índice | M22 |
| [Viagens realizadas pelos moradores](fichas/viagens.md) | `viagens` | Mil unidades | M05 |
| [Pessoas que sofreram violência nos últimos 12 meses](fichas/violencia.md) | `violencia` | Mil pessoas | M06 |
| [Vítimas de roubo nos últimos 12 meses](fichas/vitimas_roubo.md) | `vitimas_roubo` | Mil pessoas | M05 |
| [Volume de serviços](fichas/volume_servicos.md) | `volume_servicos` | Número-índice | M23 |

## Configurados, indisponíveis no snapshot (50)

| Ficha | Indicador semântico | Unidade | Método |
|---|---|---|---|
| [Informantes da pesquisa de abate bovino](fichas/abate_bovinos_v151.md) | `abate_bovinos_v151` | Unidades | M12 |
| [Peso das carcaças de bovinos abatidos](fichas/abate_bovinos_v285.md) | `abate_bovinos_v285` | Quilogramas | M12 |
| [Custo do m²: variação mensal (%)](fichas/custo_m2_v1196.md) | `custo_m2_v1196` | % | M24 |
| [Custo do m²: variação no ano (%)](fichas/custo_m2_v1197.md) | `custo_m2_v1197` | % | M24 |
| [Custo do m²: variação em doze meses (%)](fichas/custo_m2_v1198.md) | `custo_m2_v1198` | % | M24 |
| [Custo do m²: componente material](fichas/custo_m2_v2119.md) | `custo_m2_v2119` | Reais | M24 |
| [Custo do m²: componente mão de obra](fichas/custo_m2_v2120.md) | `custo_m2_v2120` | Reais | M24 |
| [Custo do m²: número-índice](fichas/custo_m2_v49.md) | `custo_m2_v49` | Número-índice | M24 |
| [Número de empresas comerciais](fichas/empresas_comerciais_v310.md) | `empresas_comerciais_v310` | Unidades | M20 |
| [Pessoal ocupado nas empresas comerciais](fichas/empresas_comerciais_v631.md) | `empresas_comerciais_v631` | Pessoas | M20 |
| [Valor adicionado bruto do comércio](fichas/empresas_comerciais_v635.md) | `empresas_comerciais_v635` | Mil Reais | M20 |
| [Valor das incorporações, obras e serviços da construção](fichas/empresas_construcao_v1241.md) | `empresas_construcao_v1241` | Mil Reais | M19 |
| [Empresas de construção atuantes nas UFs](fichas/empresas_construcao_v13808.md) | `empresas_construcao_v13808` | Unidades | M19 |
| [Pessoal ocupado na construção](fichas/empresas_construcao_v631.md) | `empresas_construcao_v631` | Pessoas | M19 |
| [Remunerações na construção](fichas/empresas_construcao_v673.md) | `empresas_construcao_v673` | Mil Reais | M19 |
| [Empresas com inovação de produto](fichas/empresas_inovadoras_v5982.md) | `empresas_inovadoras_v5982` | Unidades | M28 |
| [Empresas com inovação de processo](fichas/empresas_inovadoras_v5985.md) | `empresas_inovadoras_v5985` | Unidades | M28 |
| [Empresas com inovação de produto e processo](fichas/empresas_inovadoras_v5988.md) | `empresas_inovadoras_v5988` | Unidades | M28 |
| [Empresas no universo da pesquisa de inovação](fichas/empresas_inovadoras_v630.md) | `empresas_inovadoras_v630` | Unidades | M28 |
| [Utilização de fertilizantes por unidade de área](fichas/fertilizantes_v2398.md) | `fertilizantes_v2398` | Quilogramas por Hectare | M48 |
| [Pessoal ocupado nas unidades locais industriais](fichas/industria_uf_v631.md) | `industria_uf_v631` | Pessoas | M18 |
| [Remunerações nas unidades locais industriais](fichas/industria_uf_v673.md) | `industria_uf_v673` | Mil Reais | M18 |
| [Valor da transformação industrial (UF)](fichas/industria_uf_v811.md) | `industria_uf_v811` | Mil Reais | M18 |
| [INPC: número-índice](fichas/inpc_v2289.md) | `inpc_v2289` | Número-índice | M30 |
| [INPC: variação acumulada em doze meses (%)](fichas/inpc_v2292.md) | `inpc_v2292` | % | M30 |
| [INPC: variação acumulada no ano (%)](fichas/inpc_v68.md) | `inpc_v68` | % | M30 |
| [IPCA-15: número-índice](fichas/ipca15_v1117.md) | `ipca15_v1117` | Número-índice | M31 |
| [IPCA-15: variação acumulada em doze meses (%)](fichas/ipca15_v1120.md) | `ipca15_v1120` | % | M31 |
| [IPCA-15: variação acumulada no ano (%)](fichas/ipca15_v356.md) | `ipca15_v356` | % | M31 |
| [IPCA: variação acumulada em doze meses (%)](fichas/ipca_v2265.md) | `ipca_v2265` | % | M29 |
| [IPCA: número-índice](fichas/ipca_v2266.md) | `ipca_v2266` | Número-índice | M29 |
| [IPCA: variação acumulada no ano (%)](fichas/ipca_v69.md) | `ipca_v69` | % | M29 |
| [IPP: número-índice](fichas/ipp_v10008.md) | `ipp_v10008` | Número-índice | M32 |
| [IPP: variação mês contra o mesmo mês anterior (%)](fichas/ipp_v1394.md) | `ipp_v1394` | % | M32 |
| [IPP: variação acumulada no ano (%)](fichas/ipp_v1395.md) | `ipp_v1395` | % | M32 |
| [Informantes da pesquisa de leite](fichas/leite_adquirido_v151.md) | `leite_adquirido_v151` | Unidades | M13 |
| [Preço médio do leite cru pago ao produtor](fichas/leite_adquirido_v2522.md) | `leite_adquirido_v2522` | Reais por litro | M13 |
| [Quantidade de leite industrializado](fichas/leite_adquirido_v283.md) | `leite_adquirido_v283` | Mil litros | M13 |
| [Sobrevivência de empresas após um ano (%)](fichas/nascimentos_empresas_v13235.md) | `nascimentos_empresas_v13235` | % | M27 |
| [Sobrevivência de empresas após dois anos (%)](fichas/nascimentos_empresas_v13236.md) | `nascimentos_empresas_v13236` | % | M27 |
| [Sobrevivência de empresas após três anos (%)](fichas/nascimentos_empresas_v13237.md) | `nascimentos_empresas_v13237` | % | M27 |
| [Informantes da pesquisa de ovos](fichas/ovos_produzidos_v151.md) | `ovos_produzidos_v151` | Unidades | M14 |
| [Galinhas poedeiras nos estabelecimentos pesquisados](fichas/ovos_produzidos_v1988.md) | `ovos_produzidos_v1988` | Cabeças | M14 |
| [Estimativa da safra: área colhida](fichas/safra_area_colhida.md) | `safra_area_colhida` | Hectares | M10 |
| [Número de empresas de serviços não financeiros](fichas/servicos_nao_financeiros_v630.md) | `servicos_nao_financeiros_v630` | Unidades | M21 |
| [Pessoal ocupado nos serviços não financeiros](fichas/servicos_nao_financeiros_v631.md) | `servicos_nao_financeiros_v631` | Pessoas | M21 |
| [Valor adicionado bruto dos serviços não financeiros](fichas/servicos_nao_financeiros_v635.md) | `servicos_nao_financeiros_v635` | Mil Reais | M21 |
| [Área das unidades de conservação terrestres](fichas/unidades_conservacao_v6308.md) | `unidades_conservacao_v6308` | Quilômetros quadrados | M43 |
| [Proporção da área em unidades de conservação terrestres (%)](fichas/unidades_conservacao_v6309.md) | `unidades_conservacao_v6309` | % | M43 |
| [Distribuição das viagens por finalidade (%)](fichas/viagens_v10392.md) | `viagens_v10392` | % | M05 |

## Apoio sem KPI próprio, presente nos metadados do release (38)

| Ficha | Indicador semântico | Unidade | Método |
|---|---|---|---|
| [Percentual de pessoas quilombolas nos territórios quilombolas](fichas/apoio--censo_percentual_quilombolas_territorios.md) | `censo_percentual_quilombolas_territorios` | % | pendente |
| [Pessoas indígenas](fichas/apoio--censo_pessoas_indigenas.md) | `censo_pessoas_indigenas` | Pessoas | M01 |
| [Pessoas indígenas por idade](fichas/apoio--censo_pessoas_indigenas_idade.md) | `censo_pessoas_indigenas_idade` | Pessoas | pendente |
| [Pessoas quilombolas](fichas/apoio--censo_pessoas_quilombolas.md) | `censo_pessoas_quilombolas` | Pessoas | M01 |
| [População residente](fichas/apoio--censo_populacao_residente.md) | `censo_populacao_residente` | Pessoas | M01 |
| [População residente por sexo (tabela 9514, conferência)](fichas/apoio--censo_populacao_sexo_9514.md) | `censo_populacao_sexo_9514` | Pessoas | M01 |
| [Pessoas quilombolas residentes em territórios quilombolas](fichas/apoio--censo_quilombolas_em_territorios.md) | `censo_quilombolas_em_territorios` | Pessoas | pendente |
| [População residente por quesito de declaração indígena](fichas/apoio--censo_residentes_declaracao_indigena.md) | `censo_residentes_declaracao_indigena` | Pessoas | M01 |
| [População residente por localização em relação a territórios quilombolas](fichas/apoio--censo_residentes_territorio_quilombola.md) | `censo_residentes_territorio_quilombola` | Pessoas | M01 |
| [Pessoas residentes em territórios quilombolas](fichas/apoio--censo_residentes_territorios_quilombolas.md) | `censo_residentes_territorios_quilombolas` | Pessoas | pendente |
| [Distribuição da despesa monetária e não monetária média mensal familiar](fichas/apoio--despesa_familiar_distribuicao.md) | `despesa_familiar_distribuicao` | % | M08 |
| [Percentual de crianças com menos de 6 meses de idade que são amamentadas exclusivamente com leite materno, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_aleitamento_exclusivo_v7180.md) | `ic95_aleitamento_exclusivo_v7180` | % | M06 |
| [Percentual de crianças com menos de 6 meses de idade que são amamentadas exclusivamente com leite materno, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_aleitamento_exclusivo_v7181.md) | `ic95_aleitamento_exclusivo_v7181` | % | M06 |
| [Percentual de pessoas que consultaram médico nos últimos 12 meses, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_consulta_medica_v5363.md) | `ic95_consulta_medica_v5363` | % | M06 |
| [Percentual de pessoas que consultaram médico nos últimos 12 meses, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_consulta_medica_v5364.md) | `ic95_consulta_medica_v5364` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade com consumo abusivo de álcool nos últimos 30 dias anteriores à pesquisa, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_consumo_abusivo_alcool_v4302.md) | `ic95_consumo_abusivo_alcool_v4302` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade com consumo abusivo de álcool nos últimos 30 dias anteriores à pesquisa, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_consumo_abusivo_alcool_v4303.md) | `ic95_consumo_abusivo_alcool_v4303` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de diabetes, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_diabetes_v4466.md) | `ic95_diabetes_v4466` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de diabetes, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_diabetes_v4467.md) | `ic95_diabetes_v4467` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que possuem pelo menos uma doença crônica, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_doenca_cronica_v11221.md) | `ic95_doenca_cronica_v11221` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que possuem pelo menos uma doença crônica, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_doenca_cronica_v11222.md) | `ic95_doenca_cronica_v11222` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade com excesso de peso, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_excesso_peso_v11676.md) | `ic95_excesso_peso_v11676` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade com excesso de peso, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_excesso_peso_v11677.md) | `ic95_excesso_peso_v11677` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade fumantes atuais de tabaco, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_fumantes_v4164.md) | `ic95_fumantes_v4164` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade fumantes atuais de tabaco, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_fumantes_v4165.md) | `ic95_fumantes_v4165` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de hipertensão arterial, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_hipertensao_v4400.md) | `ic95_hipertensao_v4400` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade que referem diagnóstico médico de hipertensão arterial, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_hipertensao_v4401.md) | `ic95_hipertensao_v4401` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade insuficientemente ativas, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_insuficientemente_ativos_v4266.md) | `ic95_insuficientemente_ativos_v4266` | % | M06 |
| [Percentual de pessoas de 18 anos ou mais de idade insuficientemente ativas, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_insuficientemente_ativos_v4267.md) | `ic95_insuficientemente_ativos_v4267` | % | M06 |
| [Percentual de pessoas que tinham algum plano de saúde (médico ou odontológico), considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_plano_saude_v5265.md) | `ic95_plano_saude_v5265` | % | M06 |
| [Percentual de pessoas que tinham algum plano de saúde (médico ou odontológico), considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_plano_saude_v5266.md) | `ic95_plano_saude_v5266` | % | M06 |
| [Percentual de mulheres que realizaram pré-natal, considerando um intervalo de confiança de 95% - limite inferior](fichas/apoio--ic95_pre_natal_v6640.md) | `ic95_pre_natal_v6640` | % | M06 |
| [Percentual de mulheres que realizaram pré-natal, considerando um intervalo de confiança de 95% - limite superior](fichas/apoio--ic95_pre_natal_v6641.md) | `ic95_pre_natal_v6641` | % | M06 |
| [IPCA - Variação mensal, índice geral e grupos](fichas/apoio--ipca_grupos_variacao_mensal.md) | `ipca_grupos_variacao_mensal` | % | M29 |
| [Rendimento médio de abacaxi e coco (Frutos por Hectare)](fichas/apoio--lavouras_v112_frutos_ha.md) | `lavouras_v112_frutos_ha` | Frutos por Hectare | M09 |
| [Rendimento médio das lavouras (Quilogramas por Hectare)](fichas/apoio--lavouras_v112_kg_ha.md) | `lavouras_v112_kg_ha` | Quilogramas por Hectare | M09 |
| [Quantidade produzida de abacaxi e coco (Mil frutos)](fichas/apoio--lavouras_v214_frutos.md) | `lavouras_v214_frutos` | Mil frutos | M09 |
| [Quantidade produzida das lavouras (Toneladas)](fichas/apoio--lavouras_v214_ton.md) | `lavouras_v214_ton` | Toneladas | M09 |

## Apoio apenas configurado; publicação não comprovada (6)

| Ficha | Indicador semântico | Unidade | Método |
|---|---|---|---|
| [Coeficiente de variação - Viagens realizadas pelos moradores dos domicílios](fichas/apoio--cv_viagens_v10391.md) | `cv_viagens_v10391` | % | M05 |
| [Coeficiente de variação - Distribuição percentual das viagens realizadas pelos moradores dos domicílios](fichas/apoio--cv_viagens_v10393.md) | `cv_viagens_v10393` | % | M05 |
| [Estimativa da safra: produção de abacaxi e coco](fichas/apoio--safra_producao_frutos.md) | `safra_producao_frutos` | Mil frutos | M10 |
| [Estimativa da safra: produção (toneladas)](fichas/apoio--safra_producao_ton.md) | `safra_producao_ton` | Toneladas | M10 |
| [Estimativa da safra: rendimento de abacaxi e coco](fichas/apoio--safra_rendimento_frutos_ha.md) | `safra_rendimento_frutos_ha` | Frutos por Hectare | M10 |
| [Estimativa da safra: rendimento (kg/ha)](fichas/apoio--safra_rendimento_kg_ha.md) | `safra_rendimento_kg_ha` | Quilogramas por Hectare | M10 |
