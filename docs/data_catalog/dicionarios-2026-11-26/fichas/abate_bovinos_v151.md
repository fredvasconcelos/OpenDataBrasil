# Informantes da pesquisa de abate bovino

Ficha `abate_bovinos_v151` · indicador `abate_bovinos_v151` · **indisponivel_snapshot**.

## Significado e uso

Número de informantes

O par tabela/variável abaixo delimita a medida. A explicação acima vem do catálogo do portal; as sínteses metodológicas citadas são próprias, com fontes oficiais e limites explícitos.

- Unidade no portal: **Unidades**. Grão: território x trimestre.
- Aditividade territorial configurada: `additive`; temporal: `None`. Esses campos não autorizam somas novas.
- Sigla: não localizada em campo próprio. Datas de obtenção/publicação do dado: não reconferidas; datas dos descritores e de liberação estão no registro JSON.

## Fontes, variáveis e universos

| Dataset | Tabela/variável | Nome oficial / unidade | Método |
|---|---|---|---|
| `ibge-medida-t1092-v151` | [1092/151](https://sidra.ibge.gov.br/tabela/1092) | Número de informantes / Unidades | M12 |

Cada ligação integral em [fichas.json](../fichas.json) guarda nota, fonte produtora, calendário, liberações, exceções de nível, variável, seleção, regras Silver/Gold e licença. Os [códigos](../codigos.csv) e [campos](../campos.csv) preservam nome, descrição, indentação, unidade e exceções; descrição vazia está identificada. Não presumir cruzamento publicado pela mera presença de categorias.

### 1092 / 151

Pesquisa/produtor: Pesquisa Trimestral do Abate de Animais. Periodicidade: trimestral. Disponibilidade na fonte: 1º trimestre 1997 a 2º trimestre 2026.
Precisão de armazenamento/apresentação no descritor: 0 / 0 casas. Soma de períodos/territórios na fonte: False / True.
Nota oficial (síntese de contexto não substitui a nota): 1 - Os dados divulgados são oriundos de estabelecimentos que estão sob inspeção sanitária federal, estadual ou municipal. 2 - Os dados das Unidades da Federação com menos de 3 informantes estão desidentificados com o caracter X. 3 - O número de informantes se repete nos meses de cada trimestre devido à periodicidade de coleta da pesquisa ser trimestral. 4 - A pesquisa do abate sofreu alterações conceituais a partir de 2012. As categorias de novilhos precoces, vitelos e novilhos foram fundidos em uma só: novilhos. O mesmo vale para novilhas. 5 - Bovinos - gado doméstico, dividido em categorias conforme sexo e idade: Boi - bovino macho adulto, com 2 anos de idade ou mais. Inclui o macho não castrado (touro). Vaca - bovino fêmea adulta, com 2 anos de idade ou mais, independente de já ter parido ou não. Novilho - bovino macho jovem, com menos de 2 anos de idade. Inclui vitelo, bezerro e novilho (precoce ou não). Novilha - bovino fêmea jovem, com menos de 2 anos de idade. Inclui vitela, bezerra e novilha (precoce ou não). 6 - Peso da Carcaça - peso da carcaça quente (em Kg), entendendo-se como carcaça: o animal abatido, formado das massas musculares e ossos, desprovido de cabeça, mocotós, cauda, couro, órgãos e vísceras torácicas e abdominais, tecnicamente preparado. Nos frangos, é facultativa a retirada dos rins, pés, pescoço e cabeça. Nos suínos a carcaça pode ou não incluir o couro, a cabeça e os pés. 7 - Os dados dos 4 trimestres do ano são preliminares até a divulgação dos dados do 1° trimestre do ano seguinte.

## Publicação e operações

Release do snapshot: `f1b77232-3f14-4e63-b943-82fed4fa2886`. Presença do indicador nos metadados Gold: não. A configuração foi lida nesta revisão; o serviço ativo não foi acessível.

Períodos por nível no snapshot: `[]`.

Capacidades temporais do snapshot de implementação: `null`.

Parecer temporal preservado: `sem parecer na rodada dos 241 KPIs`.

Correções, categorias fixas, equivalências e harmonizações estão no registro JSON, sem alteração. Tabela e exportação mantêm períodos separados; Isolar + Acumular do gráfico não é uma transformação exportada (ADRs 0026/0041).

## Pesquisa e lacunas

[M12 — Abate](../pesquisas.md#m12): Quantidade de animais abatidos e peso das carcaças por espécie. A população e a edição específicas continuam sendo as da tabela/variável.

- LIVE: API, Docker e release ativo não reconferidos nesta execução; disponibilidade é a do snapshot identificado.
- CONCEITO: fechar fórmula, universo, denominador/pesos e revisão de cada variável/edição no manual completo.
- CODIGOS: nome oficial não equivale a definição conceitual; descrições vazias permanecem não localizadas.
- COBERTURA: não homologados todos os territórios/períodos/interseções; não extrapolar categorias do descritor à Gold.
- DADOS: KPI configurado ausente da navegação N2 no snapshot; candidato não significa publicado.
- M12: Rever sigilo por estabelecimento e mudança de painel em cada edição; número de informantes não recebe soma temporal.
