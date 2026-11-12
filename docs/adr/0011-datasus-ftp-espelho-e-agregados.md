# ADR-0011: DATASUS, com espelho do FTP na Bronze e agregados por município na Silver

- **Estado:** aceito pelo mantenedor (2026-11-11). Primeira fonte da Fase 6.
- **Contexto normativo:** CLAUDE.md §6, §7.3, §9, §15.4, §23, §25.2 e §28
- **Avaliação de acesso:** [`datasus-avaliacao.md`](../data_catalog/datasus-avaliacao.md)

## Contexto

O mantenedor quer usar os dados do SUS para complementar o que já vem do IBGE.
O primeiro caso são os óbitos: o Registro Civil do IBGE (tabela 2654) e o SIM
do Ministério da Saúde.

Ele também pediu para guardar toda a informação na Bronze e na Silver, porque
um endpoint ou um FTP pode sair do ar. O portal consulta só o que está no
servidor do projeto.

A unidade amostral mínima é o município: os registros individuais de óbito
não são necessários.

## Decisões

### 1. Conector `ftp_file` (FTP oficial, §7.3)

Os três caminhos oficiais respondem sem navegador: FTP, TabNet e API de dados
abertos. O FTP de transferência de arquivos é o mais completo para séries
históricas. O conector:

- **Datasets:** cada dataset é uma pasta do FTP com um padrão de nomes, e cada
  arquivo é uma partição.
- **Listagem:** `LIST` no formato DOS. O servidor do DATASUS (Microsoft FTP
  Service) não aceita `MLSD` com fatos, e os nomes vêm em Latin-1.
- **Mudanças:** detectadas pela assinatura `tamanho|data` da listagem, porque
  o FTP não tem ETag. Arquivo revisado pela fonte entra como versão nova.
- **Robustez:** tempo de espera, novas tentativas e intervalo mínimo da
  política da fonte. Falhas transitórias são adiadas e repescadas pelo
  runner (ADR-0010, decisão 11).
- **Validação:**
  - o tamanho baixado é conferido com a listagem;
  - os arquivos `.dbc` são descomprimidos e o cabeçalho DBF é lido, o que
    detecta arquivo truncado.
- **Nome na Bronze:** minúsculo, sem acentos e com sufixo do hash do nome
  original (§6.4: não depender do nome de terceiros). O nome original fica na
  chave da partição e na URL de origem.

### 2. Espelho completo do SIM e do SINASC na Bronze

A configuração está em `configs/sources/datasus.toml`, com 32 datasets, um por
pasta:

- microdados `.dbc`: CID-10 e CID-9, óbitos fetais, preliminares e nascidos
  vivos nos leiautes antigo e novo;
- definições do TabWin;
- tabelas auxiliares;
- documentação em PDF.

O total medido em 2026-11-11 foi de cerca de 18 GB, com 923 GB livres (§25.2).
Os sistemas maiores (SIH, SIA) ficam para outra decisão, por causa do volume.

Os datasets ficam com `access_classification = "restricted"`, porque os
microdados contêm registros individuais. Eles não saem da Bronze e da Silver
interna.

### 3. Leitura do `.dbc`: `datasus-dbc` (MIT) e `dbfread` (MIT)

O `.dbc` é um DBF comprimido com *blast* (PKWare). A escolha, delegada pelo
mantenedor, foi `datasus-dbc==0.1.3`: MIT, sem dependências, com pacote pronto
para Python 3.12 no Linux. A leitura do DBF fica com `dbfread==2.0.7` (MIT).

Alternativas descartadas:

- `pyreaddbc`: AGPL-3.0, uma licença copyleft que imporia obrigações ao serviço
  público;
- `pysus`: GPL e muitas dependências.

### 4. Silver: Total e cada dimensão por município (sem cruzamento)

O transformador `datasus_sim_do` lê `DO<UF><ano>.dbc` e gera, no contrato de
observação da Silver (o mesmo do SIDRA, `table_id = "SIM-DORES"`):

- **Nível 6 (município de residência):** o código de 6 dígitos do DATASUS é
  convertido no código IBGE de 7 dígitos pela DTB.
- **Nível 3 (UF):** todos os óbitos de residentes da UF, inclusive os de município
  ignorado ou sem correspondência na DTB.
- **Dimensões:**
  - sexo;
  - faixa etária (decodificada do código de 3 dígitos do SIM);
  - cor ou raça;
  - capítulo da CID-10 da causa básica;
  - local de ocorrência.
- **Desenho das tabelas do SIDRA:** em cada território vêm o Total (categoria
  `T`) e a distribuição de cada dimensão, com as demais no Total.
- **Sem cruzamento:** cruzar as cinco dimensões manteria quase um registro por
  óbito (3.668 linhas para 4.189 óbitos no Acre em 2023). Isso traria risco de
  reidentificação em municípios pequenos (§23) e não serve ao panorama. Com o
  desenho escolhido, são 925 linhas para a mesma UF e o mesmo ano.
- **Conferência:** a soma de cada dimensão é comparada ao número de registros
  lidos, então nenhum óbito se perde.
- **Arquivo nacional `DOBR<ano>.dbc`:** a pasta traz, além das 27 UFs, um arquivo do
  Brasil com os mesmos registros. Ele não entra na soma, porque contaria cada óbito
  duas vezes. Só o número de registros dele é lido, pelo cabeçalho do DBF, e
  comparado à soma das UFs no ano (verificação `sim.national_file`, aviso).
- **UF de residência pelo código do município (decisão do mantenedor, 2026-11-12):**
  vale o prefixo do código de residência, não o arquivo em que o registro veio. Tocantins
  existe desde a Constituição de 1988 e o SIM CID-10 começa em 1996, então todo residente
  de Tocantins conta em Tocantins. Isso afeta 24 óbitos, registrados em `DOGO1999.dbc` e
  `DOGO2001.dbc`: eles saem de Goiás e entram nos municípios e no total de Tocantins.
  - A Silver monta os 27 arquivos de cada ano antes de agregar. Sem código válido,
    fica a UF do arquivo.
  - A linha de cada UF aponta para o arquivo da própria UF. Os registros vindos de
    outro arquivo ficam listados na verificação `sim.other_uf_residents` (aviso).
- **Nível 1 (Brasil):** soma de todos os registros do ano. Só é gerado quando a
  contagem do `DOBR<ano>.dbc` confere com a soma das UFs, e as linhas apontam para esse
  arquivo. Hoje isso vale para os 29 anos.

### 5. Complementar ou novo KPI (decisão do mantenedor)

Os dados do SUS são comparados com os do IBGE antes de qualquer uso conjunto
(§15.4):

- se forem complementares (mesmo conceito, cobertura compatível), completam a
  série, com fonte, notas e referências;
- se não forem, entram como KPI novo, separado do KPI do IBGE.

Para os óbitos, a comparação é SIM × Registro Civil por UF e ano, e o
resultado vai para `docs/data_catalog/` antes de entrar na Gold.

**Resultado (2026-11-12):** [`comparacao-obitos-sim-registro-civil.md`](../data_catalog/comparacao-obitos-sim-registro-civil.md),
gerado da Silver do SIM (1996–2024) e da tabela 2654 (2003–2024).

- **Brasil:** o SIM conta de 1,1% a 3,2% a mais que o Registro Civil em todos os anos.
- **UFs:** só 37% dos 594 pares UF × ano ficam a até 2%. A diferença se concentra no
  Norte e no Nordeste, como Maranhão (média de 127,6%), Pará (116,1%) e Piauí (112,8%),
  onde o sub-registro em cartório é conhecido. Sul, Sudeste e Centro-Oeste ficam perto
  de 100%.
- **Conclusão:** cobertura não compatível. Pela regra acima, o SIM entra como **KPI
  novo**, não como complemento da série do IBGE.
- **KPI criado (aprovado pelo mantenedor em 2026-11-12):** "Óbitos por residência
  (SIM)" (`sim_obitos_residencia`), no tema Saúde, subtema Mortalidade (item `externos`
  do panorama).
  - Configuração: `configs/indicators/demografia/obitos_sim.toml` e
    `configs/portal/demografia/obitos_sim.toml`.
  - Níveis: município, UF e Brasil. Série anual desde 1996.
  - Esta versão leva o Total. As cinco dimensões da Silver ficam fixas em "T" no fato.
  - O detalhe por sexo e por faixa etária exige nomes de dimensão próprios na Silver,
    porque "Sexo" já é a dimensão da classificação c2 do IBGE.
  - O dataset aponta para a pasta `CID10/DORES` (`restricted`, por causa dos
    microdados da Bronze). A Gold só publica as contagens agregadas.

### 6. Licença

O metadado oficial do conjunto SIM em `dadosabertos.saude.gov.br/dataset/sim`
traz `license_id: cc-by` (Creative Commons Atribuição), verificado em
2026-11-11. Outras licenças encontradas não se aplicam aos dados:

- a página de acesso à informação do DATASUS não traz termo de reúso;
- o rodapé do portal (CC BY-ND 3.0) vale para o conteúdo do site;
- o MIT da API vale para o software.

A licença `ms-dados-abertos-cc-by` fica em `requires_review` até a confirmação
de que cobre os arquivos do FTP.

## Consequências

- **Preservação:** a Bronze guarda uma cópia de tudo do SIM e do SINASC,
  independente da disponibilidade da fonte.
- **Gold:** ainda não lê a Silver do DATASUS. A entrada na Gold depende da
  comparação (decisão 5) e de generalizar a Gold para transformadores além do
  `sidra_observation`.
- **Próximos passos:**
  - Silver do SINASC (nascidos vivos), no mesmo desenho;
  - SIM da CID-9 (1979 a 1995), com o próprio mapa de capítulos;
  - comparação com o Registro Civil (tabelas 2654 e 2609).
