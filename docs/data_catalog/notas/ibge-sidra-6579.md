# Notas oficiais da tabela SIDRA 6579 (População residente estimada)

- **Fonte:** https://sidra.ibge.gov.br/tabela/6579 (seção "Notas")
- **Obtenção:** transcrição manual feita pelo mantenedor do projeto em
  2026-11-03. Os endpoints de metadados do SIDRA respondem 403 a clientes
  automatizados, e esse bloqueio não foi contornado.
- **Uso:** documentação e interpretação. Os valores da tabela não são
  alterados com base nestas notas.
- Histórico de alterações indicado pela fonte:
  https://www.ibge.gov.br/estatisticas-novoportal/sociais/populacao/9103-estimativas-de-populacao.html

## Notas que explicam divergências de reconciliação (verificadas)

| Ano | Nota (resumo) | Verificação nos dados |
|---|---|---|
| 2004 | "Inclusive 4 municípios com instalação prevista para 1º de janeiro de 2005: Aroeiras do Itaim (PI), Figueirão (MS), Ipiranga do Norte (MT) e Itanhangá (MT)." | Soma dos municípios − total da UF: PI +2.561 = Aroeiras do Itaim; MS +2.908 = Figueirão; MT +6.499 = Ipiranga do Norte (2.445) + Itanhangá (4.054) |
| 2008 | "Inclusive o Município de Nazária - PI, com previsão de instalação em 1º de janeiro de 2009." | PI +7.817 = Nazária |
| 2012 | "Municípios instalados em 1º de janeiro de 2013." | PA +15.018 = Mojuí dos Campos; SC +20.552 = Pescaria Brava (9.416) + Balneário Rincão (11.136); RS +2.578 = Pinto Bandeira; MS +4.723 = Paraíso das Águas |

Interpretação: municípios com instalação prevista recebem estimativa própria,
mas a população deles continua contada também no município de origem. Os totais
oficiais de UF, Grande Região e Brasil contam essas pessoas uma vez só; a soma
das estimativas municipais conta duas vezes.

## Demais categorias de notas (não afetam a reconciliação)

- **Populações judiciais (2009 em diante):** valores definidos por decisão
  judicial "para efeito de distribuição do Fundo de Participação dos
  Municípios". Às vezes são uma faixa ("entre 10.189 e 13.584"). **Não
  substituem** o valor publicado na tabela.
- **Correções de enumeração:** Caraíbas-BA reduzido em 5.006 habitantes (2003
  e 2004) após sindicância sobre o Censo 2000.
- **Mudanças de nome:** Santarém-PB → Joca Claudino-PB (23/11/2010) e Campo de
  Santana-PB → Tacima-PB (30/12/2009), citados na nota de 2011.
- **Arredondamento (2011):** a população do Brasil difere em 2.791 pessoas da
  divulgada no D.O.U. de 31/08/2011, por causa do novo critério de
  arredondamento.
- **Limites territoriais (2013–2017 e 2018–2021):** diferenças entre a soma das
  estimativas municipais por UF e as Projeções de População se devem a
  alterações de limites entre estados após o Censo 2010. Nos dados da API, os
  totais de UF conferem com a soma municipal nesses anos.
- **Alterações de limites municipais:** Livramento-PB e Taperoá-PB (2016 a
  2018); Acarape-CE, Aracoiaba-CE e Barreira-CE (2018).

## Texto de referência

Os resumos acima não substituem o texto oficial. Consulte as notas completas na
própria tabela (https://sidra.ibge.gov.br/tabela/6579). Elas incluem a lista
de populações judiciais por ano, com os números dos processos.
