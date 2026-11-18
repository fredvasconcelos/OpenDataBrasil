# ADR-0024: "Detalhar por" como filtro hierárquico

- **Estado:** aceito (2026-11-14), por pedido do mantenedor.
- **Contexto normativo:** CLAUDE.md §15.4, §18.4 (fluxo de consulta) e §19.7 (o frontend
  não decide sozinho o que pode ser somado).

## Contexto

Antes, "Detalhar por" só ligava ou desligava uma dimensão inteira. Com muitas
categorias (rebanhos, produtos, idades), o mantenedor quer escolher uma combinação
livre ("Bovino e Caprino") e ver tudo recalculado nessa seleção.

## Decisões

1. **Lista hierárquica na barra lateral:**
   - a dimensão, ao ser marcada, marca todas as suas categorias;
   - cada categoria pode ser marcada à parte;
   - com só algumas marcadas, a dimensão fica "parcial";
   - categorias com nomes curtos ficam em duas colunas.
2. **Parâmetro `categories` na API.** É aceito no mapa, no tooltip, na série, na tabela
   e na exportação, com chaves como `c79:2670`.
   - A API aceita só as categorias da partição exposta; outra chave dá 422.
   - Marcar todas as categorias equivale a não filtrar.
3. **Recálculo no backend** (`filter_totals`): nos indicadores somáveis (a mesma regra
   do %, `allows_category_shares`), o Total de cada dimensão filtrada vira a soma das
   categorias marcadas, com status `derived_sum`.
   - Partes "..." ou ausentes ficam fora da soma, como nos grupos (ADR-0023).
   - Uma parte suprimida bloqueia a soma.
   - Com dimensões cruzadas, a soma usa só as células marcadas nas duas dimensões.
4. **Indicadores não somáveis** (taxas, médias): o filtro só limita as categorias
   mostradas; o Total continua o oficial. O portal avisa isso.
5. **URL:** `cat=c79:2670,c79:2681`, junto de `dim`. As categorias de dimensões
   desligadas saem da URL, e as seleções completas também.

## Consequências

- **Total da seleção:** o mapa, o tooltip, a série, a tabela (com o rodapé) e as
  exportações mostram a mesma seleção. O % é calculado sobre a soma marcada.
- **Gold intocada:** a soma é feita na consulta (§10.7), sem gravar nada.
