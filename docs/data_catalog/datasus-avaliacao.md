# DATASUS: avaliação das formas de acesso

Avaliação de 2026-11-11, feita a pedido do mantenedor e testada com requisições
reais a partir do ambiente de desenvolvimento (Espanha). É a base para o plano
da Fase 6 (segunda fonte), que ainda precisa de aprovação (§28). Nada foi
ingerido.

## Resumo

Os quatro caminhos oficiais respondem daqui, sem login, CAPTCHA ou desafio do
Cloudflare. Nenhum deles precisa de automação de navegador: todos são HTTP ou
FTP simples. Pelo §7.3, a automação de navegador só entra quando não há
alternativa oficial, e aqui há.

| Caminho | O que traz | Uso recomendado |
|---|---|---|
| **FTP de transferência de arquivos** (`ftp.datasus.gov.br/dissemin/publicos/`) | microdados por sistema, UF e ano, em `.dbc` (DBF comprimido); definições do TabWin (`.def`, `.cnv`); documentação em PDF | fonte principal das séries históricas (SIM, SINASC, SIH, CNES, SINAN...) |
| **TabNet** (`tabcgi.exe`, POST do formulário) | tabulações oficiais prontas (linha × coluna × medida), também de bases antigas sem microdados no FTP | conferência (reconciliação) e tabelas sem microdados, como o saneamento dos Censos 1991, 2000 e 2010 |
| **API de Dados Abertos** (`apidadosabertos.saude.gov.br`, Swagger 1.8.32, 116 endpoints) | registros paginados (`limit`/`offset`) de CNES, SISAGUA, vacinação, SIM, SINASC, SIH... | cadastros com filtro (CNES por UF e município, SISAGUA); não serve para baixar séries longas de SIM e SINASC (sem filtro de ano nem de UF) |
| Portal `dadosabertos.saude.gov.br` | catálogo e arquivos para baixar | a API CKAN antiga (`opendatasus`) responde 404; usar a API acima |

## Testes realizados

- **Páginas indicadas**: todas responderam HTTP 200.
  - `tabdescr.htm`, as instruções do TabNet e do TabWin;
  - "Informações de saúde (TabNet)";
  - "Saneamento: Censos 1991, 2000 e 2010";
  - `deftohtm.exe?ibge/cnv/aagbr`, o formulário do abastecimento de água;
  - "Transferência de arquivos".
- **TabNet**: um POST com os mesmos campos do formulário devolveu a tabulação
  de abastecimento de água nos Censos de 1991, 2000 e 2010:
  - campos: `Linha`, `Coluna`, `Incremento`, `Arquivos=agubr10.dbf,agubr00.dbf,agubr91.dbf`,
    filtros `S*=TODAS_AS_CATEGORIAS__` e `formato=prn`;
  - Brasil: 34.734.715, 44.795.101 e 57.324.167 domicílios;
  - formato: texto separado por `;`, com a hierarquia das categorias marcada por
    `..` e `....` (o mesmo princípio da indentação dos descritores do SIDRA) e `-`
    para "não se aplica";
  - os nomes das categorias vêm em entidades HTML (`&ccedil;`), na codificação
    Latin-1.
- **FTP**:
  - `SIM/CID10/DORES` tem 812 arquivos `DO<UF><ano>.dbc`, de 1996 a 2024,
    somando cerca de 4,8 GB comprimidos;
  - `SIM/CID10/TAB` tem as conversões do TabWin (`CNVS_CID10_v2019.rar`,
    `OBITOS_CID10_TAB.zip`), e `SIM/CID10/DOCS`, a estrutura do SIM (PDF);
  - `IBGE/censo` tem só alfabetização, escolaridade, idosos e renda, por isso o
    saneamento dos Censos vem do TabNet.
- **API**: o endpoint do SIM devolve registros individuais de óbito
  (`causabas`, `codmunres`, `idade`, `racacor`...), sem filtro de período.
- `robots.txt`:
  - `datasus.saude.gov.br` só restringe `/wp-admin/`;
  - o TabNet e a API não publicam `robots.txt` (404).

## Proposta de arquitetura (para aprovação)

1. **Conector FTP** (`ftp_file`, tipo previsto no §7.3):
   - lista o diretório, baixa `.dbc` por UF e ano e preserva os bytes na
     Bronze com SHA-256;
   - detecta mudanças pela data e pelo tamanho do arquivo listado (o FTP não
     tem ETag);
   - reprocessa os anos recentes, porque o SIM e o SINASC são revisados.
2. **Leitura do `.dbc`** na Silver: o `.dbc` é DBF comprimido pelo algoritmo
   *blast* (PKWare). Exige uma biblioteca de descompressão de código aberto
   (candidatas: `pyreaddbc`, `datasus-dbc`). Antes de adotar, é preciso
   conferir a licença e a manutenção, e testar contra o TabNet.
3. **Conector TabNet** (`tabnet`, "sistema de tabulação" no §7.3):
   - envia o POST do formulário, com a definição (`.def`) e os campos
     declarados na configuração e conferidos no próprio formulário (sem
     inventar campos);
   - guarda a resposta crua na Bronze;
   - a Silver lê a hierarquia `..` como a indentação do SIDRA.
4. **Privacidade (§23)**:
   - os microdados do SIM e do SINASC são públicos, mas são registros
     individuais;
   - eles ficam só na Bronze e na Silver, com acesso interno;
   - a Gold publica só agregados (município × ano × categoria), com regra de
     supressão de células pequenas a definir;
   - nada de registro individual no portal nem na API.
5. **Compatibilidade com o IBGE (§15.4)**:
   - o SIM e o SINASC (Ministério da Saúde) e o Registro Civil (IBGE, tabelas
     2609 e 2654) medem eventos parecidos, mas com fontes e coberturas
     diferentes;
   - na Gold, ficam como indicadores distintos, marcados como
     "compatibilidade incerta" até haver uma regra documentada;
   - o portal não soma nem mistura os dois.
6. **Primeira entrega sugerida**:
   - saneamento dos Censos 1991, 2000 e 2010 (TabNet, por município). Completa
     o tema Saneamento com série histórica, que o SIDRA não tem nesse formato;
   - óbitos por causa básica, capítulo da CID-10 (SIM, FTP), por município e
     ano, de 1996 em diante;
   - reconciliação: totais do SIM contra o TabNet, e contra o Registro Civil
     só como comparação documentada.

## Pendências antes de implementar

- Licença de reúso dos dados do DATASUS e do Ministério da Saúde: texto
  oficial a localizar. Fica `requires_review` até lá (como a licença do IBGE,
  KI-003).
- Biblioteca de `.dbc`: licença, manutenção e teste.
- Espaço: a carga completa do SIM tem cerca de 4,8 GB comprimidos. Os demais
  sistemas (SIH, SIA) são bem maiores. A proposta começa por recortes.
