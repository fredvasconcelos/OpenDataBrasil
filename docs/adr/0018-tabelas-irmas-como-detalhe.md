# ADR-0018: Tabelas-irmãs como detalhe do KPI

- **Estado:** aceito (2026-11-13). O mantenedor pediu "o máximo de detalhe possível",
  como idade, sexo e cor ou raça, consultando de novo as tabelas na origem, e delegou
  as decisões.
- **Usa:** ADR-0016 (série de tabelas e regras por tabela de origem) e ADR-0014
  (classificações próprias).
- **Contexto normativo:** CLAUDE.md §3.2, §9.2, §15.4 e §28.5.

## Contexto

O SIDRA publica a mesma variável em tabelas irmãs, cada uma com um recorte. Por
exemplo, as pessoas com hipertensão (PNS, variável 4396) estão:
- na 4418, por sexo e situação do domicílio, que é a tabela do KPI;
- na 4419, por idade;
- na 4420, por instrução;
- na 4421, por cor ou raça;
- na 4422, por rendimento;
- na 4423, por condição na força de trabalho.

O inventário do acervo (2026-11-10) agrupa essas tabelas em famílias. Os descritores
oficiais de 67 irmãs foram baixados em 2026-11-13 e conferidos um a um.

## Decisões

1. **Critério de entrada.** A irmã entra como detalhe do KPI quando:
   - tem a mesma variável e a mesma unidade publicada. A Gold confere a unidade:
     "%" e "Proporção (%)" ficam separadas;
   - tem períodos em comum com a base;
   - tem exatamente uma classificação nova, e ela tem Total no descritor.

   O campo `complementos` do item do panorama lista as irmãs, e o gerador as confere
   contra os descritores.
2. **Sem Total duplicado.** A irmã pede só as categorias da classificação nova, e as
   classificações em comum ficam no Total. O Total do KPI vem só da base.
3. **Série.** A base e as irmãs formam a série `ibge-serie-<tabela base>` (ADR-0016),
   com a base como representante. As regras por tabela dizem:
   - **na base:** as dimensões fixas e o Total implícito das classificações novas;
   - **em cada irmã:** as classificações comuns fixas e o Total implícito das
     classificações do fato que ela não tem.
4. **Classificações:** uma classificação curada é reaproveitada quando contém as
   categorias. Senão, entra uma própria (ADR-0014), atribuída à série.
5. **Portal:** os detalhes são marginais, um por vez (ADR-0016). A nota do indicador
   lista as irmãs e o recorte de cada uma.
6. **Volume:** valem as regras dos detalhes. O município só entra com até três
   períodos, e o limite é de 45.000 valores por requisição.

## Resultado (2026-11-13)

| Situação | KPIs e tabelas-irmãs |
|---|---|
| **Entraram:** 15 KPIs, 49 irmãs | PNS: hipertensão, diabetes, doença crônica, fumantes, álcool, atividade física, plano de saúde, consulta médica, pré-natal e violência (cor ou raça, idade, instrução, rendimento, força de trabalho); analfabetismo (cor ou raça); nível de instrução (cor ou raça); pobreza (cor ou raça); PNAD de segurança: sensação de segurança e vítimas de roubo (cor ou raça, idade, instrução, meio de informação) |
| **Recusadas** | pobreza por sexo (6825): a unidade é "%", contra "Proporção (%)" na base; PNAD Contínua trimestral (10361 a 10363, 10378 e 10379): as irmãs são anuais (médias oficiais); rendimento médio (10374 a 10376): a unidade é Mil Reais, contra Reais na base; arranjos domiciliares (9553 a 9558): as irmãs são de outro assunto (segurança alimentar); 1187 e 7269: sem classificação nova; família da população do Censo (608, 2079, 136, 3326, 6786): não avaliadas, porque a 9606 já traz sexo, idade e cor ou raça |
| **Fora do gerador** | POF de 1995 (414, com as irmãs 434 e 435 por idade e instrução do chefe), porque o KPI é curado à mão (pendência) |

## Consequências

- KPIs da PNS e da PNAD ganham cor ou raça, idade, instrução e rendimento, cada
  recorte da sua tabela oficial e rastreável pela tabela de origem.
- As irmãs não permitem cruzar recortes, por exemplo idade e cor ou raça juntas.
  Isso continua dependendo de uma tabela que publique o cruzamento.
