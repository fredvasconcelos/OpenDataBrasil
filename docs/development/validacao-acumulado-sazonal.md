# Auditor da estratégia Isolar + Acumular

O script `infrastructure/scripts/validacao_acumulado_sazonal.py` implementa uma
avaliação metodológica e um protótipo de soma para a ADR-0041. Não é chamado pelo
portal/API, não altera configurações nem escreve na Gold.

```bash
python -I infrastructure/scripts/validacao_acumulado_sazonal.py \
  --evidence /evidencias/validacao-sazonal \
  --source-evidence /evidencias/revisao-detalhamento
```

O primeiro diretório contém `portal-navigation.json` e `indice-series.json`, com
uma resposta de `GET /api/v1/kpis/{id}/series?geography=...` por KPI. O índice
registra `url`, `status`, `retrieved_at`, `sha256`, `path` e `geography`.
Escolher o território a partir dos níveis do KPI e da busca `/api/v1/geographies`,
sem presumir que todos tenham Brasil. Guardar cada resposta em diretório próprio.

O segundo contém `gold-metadata.json` (release e linhagem) e o índice de
descritores da auditoria de detalhamento. A variável é confirmada por membro
da linhagem, e não herdada da primeira tabela da família. Os hashes e releases
são verificados; séries truncadas são recusadas.

Saídas: `validacao-kpis.json`, com parecer por KPI e experimentos, e
`validacao-kpis.csv`. Os pareceres distinguem soma com método sustentado,
comparação sem soma, fluxo com método pendente e composição contígua.
Os doze perfis anuais explícitos exigem `PermiteSomaPeriodos=true` em todas as
variáveis vinculadas; um perfil divergente interrompe o auditor.

O protótipo agrupa parcelas nativas pelo mês/trimestre/semestre correspondente
no intervalo inclusivo de anos. Anual tem um único grupo do intervalo. Não
desagrega uma frequência maior nem mistura subtotais e parcelas. Valores de
categorias/séries diferentes devem ser processados separadamente.

Ausência comum permite subtotal com aviso; nenhuma parcela resulta em ausência,
sem zero inventado. Sigilo, não aplicável e erro bloqueiam a soma automática.
Zeros presentes contam na cobertura. O retorno é de auditoria, sem equivaler
os campos e status a um contrato público já implementado.

As experiências usam 2023–2025 e 2023–2026 para os perfis de soma, em uma
série/território por KPI. Datas fora da publicação são posições esperadas da
seleção; não são novas observações oficiais. Nem essas amostras nem o parecer
metodológico certificam todos os territórios, categorias ou revisões históricas.
