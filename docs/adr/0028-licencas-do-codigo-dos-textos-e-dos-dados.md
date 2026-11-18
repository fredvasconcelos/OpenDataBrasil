# ADR-0028: Licenças do código, dos textos e dos dados

- **Estado:** aceita (2026-11-18), pelo mantenedor.
- **Motiva:** a separação do repositório em um aberto (código e metodologia) e um privado
  de operação, e a hipótese de, no futuro, oferecer um produto de apoio à decisão sobre a
  plataforma.
- **Relaciona-se com:** ADR-0001 (item 9, licença de dados por dataset) e ADR-0011 (§6), que
  citam a licença MIT do código; esta decisão os substitui nesse ponto. CLAUDE.md §1.2 e §23.

## Contexto

O código estava sob a licença MIT desde a Fase 1. Três fatos levaram a revisá-la:

1. **O repositório vai ser dividido.** Um repositório aberto novo nasce de uma cópia limpa, e
   o atual vira o privado de operação. A abertura é o momento natural de escolher a licença.
2. **Pode haver, no futuro, um produto** de apoio à decisão (indicadores do município, contas
   públicas, modelos de ML e LLMs por um servidor MCP). O valor dele estaria nos dados
   harmonizados com linhagem, nas regras de compatibilidade, no modelo de decisão e na marca,
   não no código de ingestão e tratamento.
3. **Os textos e os dados não tinham licença declarada à parte do código.**

Alternativas avaliadas para o código:

| Alternativa | A favor | Contra |
|---|---|---|
| Manter a MIT | Simples, sem barreira para ninguém | Não diz nada sobre patentes nem sobre a marca |
| **Apache 2.0** | Tão permissiva quanto a MIT; concessão explícita de patentes; **não licencia a marca** (seção 6); arquivo `NOTICE` para a atribuição | Texto mais longo |
| AGPL + licença comercial | Impede que alguém hospede uma versão modificada sem abrir o código | Afasta parte das empresas e instituições; só faz sentido se o produto for a própria plataforma hospedada |
| Tudo fechado | Nada exposto | Contraria a missão e o CLAUDE.md §1.2 ("utilizar sempre software open source") |

## Decisão

1. **Código: Apache 2.0** (`LICENSE`), com o `NOTICE` na raiz. Vale para o repositório aberto
   e para o código publicado daqui em diante.
2. **Textos** (documentação, ADRs, metodologia e catálogo de dados): **CC BY 4.0**. Qualquer
   pessoa pode reaproveitar, desde que cite o Open Data Brasil.
3. **Dados:** não são licenciados pelo projeto. Cada dataset segue a licença e as condições
   de reutilização da fonte original, já registradas no catálogo (`license_id`) e mostradas
   no portal. O projeto não impõe condições mais restritivas que as da fonte.
4. **Marca:** o nome e a marca "Open Data Brasil" não são licenciados (seção 6 da Apache 2.0).
   O registro no INPI tem custo de taxas e fica para decisão do mantenedor.
5. **Estratégia, se houver produto:** núcleo aberto e produto fechado. A plataforma
   (ingestão, Gold, API, portal e um servidor MCP só de consulta, com a proveniência de cada
   número) fica aberta. A camada que recomenda e otimiza decisões ficaria num repositório
   privado à parte, com licença proprietária.

## Consequências

- O código **já publicado sob a MIT** (o histórico do repositório atual) continua MIT para
  sempre naquelas versões. A Apache 2.0 vale para o que for publicado a partir desta decisão.
- `apps/api/pyproject.toml`, `apps/portal/package.json` e a raiz do `package-lock.json` passam
  a declarar `Apache-2.0`. O README explica as três licenças.
- Ícones e bandeiras de terceiros mantêm as próprias licenças, cujos arquivos acompanham os
  ativos (Bootstrap Icons, MIT; bandeiras das UFs, CC0).
- **Ressalva:** código escrito em grande parte com ajuda de IA tem proteção de direito autoral
  incerta em várias jurisdições. Antes de qualquer produto, consultar um advogado sobre
  licenças, LGPD e venda ao setor público. O diferencial do produto deve estar nos dados, no
  modelo e na marca.

## Pendências

- Registro da marca no INPI (decisão e custo do mantenedor).
- Ao abrir o repositório novo, conferir que `LICENSE`, `NOTICE` e o README estão na raiz e que
  o guarda de fronteira não barra nenhum deles.
