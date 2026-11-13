# ADR-0021: Edições de uma pesquisa em série (Censos anteriores)

- **Estado:** aceito (2026-11-13). O mantenedor pediu a série histórica completa do
  Censo Demográfico antes da varredura do dados.gov.br.
- **Amplia:** ADR-0016 (séries de tabelas) e ADR-0018 (tabelas-irmãs).
- **Contexto normativo:** CLAUDE.md §3.2, §13.2, §14.1, §15.4 e §28.5.

## Contexto

O SIDRA publica cada Censo em tabelas próprias. Em 2026-11-13, os descritores oficiais
dos temas de população e domicílios mostraram 410 tabelas do Censo:
- 85 de 1991, 119 de 2000, 97 de 2010 e 60 de 2022;
- 36 já em série de vários anos, como a 1286 (1872 a 2010), a 1209 (1872 a 2022), a 202
  (1970 a 2010) e a 136 (1991 a 2010).

As tabelas de 2022 usam códigos de variável novos (domicílios: 381 em 2022, 96 ou 2048
antes), e às vezes o conceito também muda ("domicílios particulares permanentes
ocupados" em 2022, "domicílios particulares permanentes" em 2010). A página de séries
históricas do IBGE responde 403 a clientes automatizados e não foi usada (§7.3).

## Decisões

1. **Campo `edicoes` no panorama:** tabelas com a **mesma variável** (código e
   unidade) em outros períodos. O gerador:
   - pede só os anos que a base e as edições anteriores da lista não têm (parâmetro
     `periods` do conector);
   - pede as classificações em comum com o fato, com o Total e só as categorias que o
     fato já tem. As próprias da edição (ex.: "Sem declaração" de cor ou raça em 1991)
     ficam no Total e vão para a nota;
   - fixa no Total as demais classificações da edição; as do fato que a edição não
     tem entram no Total delas (`missing_as_total`);
   - recodifica o Total quando o código muda (`recode_categories`) e renomeia a
     dimensão quando o nome muda (`rename_dimensions`);
   - junta tudo na série `ibge-serie-<base>` (ADR-0016) e escreve a nota "Série com
     outra edição".
2. **Só até UF:** os municípios de 1991 e 2000 incluem códigos que mudaram depois. A
   harmonização territorial (§13.3) é outra etapa.
3. **Mesma variável, e não variável equivalente:** quando o código ou a unidade muda,
   a edição é recusada com o motivo. Equivalências de conceito ("permanentes" ×
   "permanentes ocupados") são decisões estatísticas e ficam curadas à mão, com nota,
   como na POF (ADR-0016), depois da aprovação do mantenedor.

## Consequências

- **Primeira edição gerada:** a 1209 traz 2022 para "População nos Censos", que vai
  de 1872 a 2022.
- **KPIs curados** (densidade, cor ou raça, população por sexo): as edições são
  limpas (mesma variável), mas os fatos são do núcleo do MVP, com fixtures e testes.
  Ficam para uma etapa curada.
- **Inventário e decisões por KPI:**
  [censo-serie-historica.md](../data_catalog/censo-serie-historica.md).
