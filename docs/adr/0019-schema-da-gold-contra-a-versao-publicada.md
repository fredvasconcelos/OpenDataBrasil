# ADR-0019: Schema da Gold conferido contra a versão publicada

- **Estado:** aceito (2026-11-13). Decisão delegada pelo mantenedor (ponto 18 do
  relatório de pontos críticos).
- **Contexto normativo:** CLAUDE.md §9.3, §10.9, §16.4, §17.3 e §22.3.

## Contexto

Antes de gravar, a Gold confere o schema de cada tabela contra o contrato. Uma
mudança incompatível, como uma coluna removida, bloqueia a construção. A conferência
usava a **última versão gravada**. Em 2026-11-13, uma construção que falhou numa
verificação final já tinha gravado uma coluna nova no fato da pobreza. A construção
seguinte, com a configuração corrigida, foi barrada por uma coluna que nenhum release
usava.

Escrita Delta não é publicação (§10.9). O que precisa de proteção é o que os releases
fixaram, e não o resto de uma construção que falhou.

## Decisão

1. **Troca automática de schema, só quando todas estas condições valem:**
   - a tabela tem alguma versão fixada em um release validado, ativo ou antigo;
   - as versões depois da última publicada nunca foram publicadas;
   - o schema da última versão publicada é compatível com o contrato atual.

   Nesse caso, a construção regrava a tabela com o schema do contrato
   (`schema_mode = overwrite`) e registra a verificação `schema.reset` com aviso e o
   motivo.
2. **Continua bloqueado:**
   - mudança incompatível em relação à versão publicada (por exemplo, remover uma
     coluna que um release usa);
   - tabela que nunca foi publicada, porque pode ter sido escrita fora do pipeline.

   Nesses casos, só o operador decide, com
   `odb gold build --reset-schema <tabela>`.
3. **Histórico preservado:** as versões anteriores continuam legíveis por versão. Os
   releases fixados leem exatamente o que liam antes (§17.3). A retenção do histórico
   segue a política do vacuum (ADR-0003).

## Consequências

- Uma construção que falha não trava a próxima por causa do schema.
- A opção manual fica para mudanças deliberadas, por exemplo a remoção definitiva de
  uma coluna publicada, com o registro do pedido na execução.
