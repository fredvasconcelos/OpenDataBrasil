# Como contribuir

O desenvolvimento é conduzido pela equipe do projeto. Não recebemos pull requests
externos neste momento. Relatos de erro nos dados e no portal são bem-vindos nas
[issues](https://github.com/fredvasconcelos/OpenDataBrasil/issues).

Informe o indicador, território, período, filtros, resultado observado e link da
fonte oficial. Inclua o release mostrado pelo portal quando disponível. Evite dados
pessoais, credenciais, arquivos de configuração local e material de acesso restrito.
Para vulnerabilidades, siga [SECURITY.md](SECURITY.md).

## Convenções

Textos, comentários, docstrings e mensagens de commit são em português do Brasil.
Identificadores seguem o padrão em inglês do código existente. A especificação é o
[CLAUDE.md](CLAUDE.md). Não altere granularidade, agregações ou metodologia sem decisão
explícita e documentação. Não edite arquivos gerados à mão.

## Guarda da distribuição pública

Instale o gancho antes de criar commits:

```bash
git config core.hooksPath .githooks
python3 -I infrastructure/scripts/public_boundary.py
```

O mesmo guarda é executado pelo CI. Ele examina **o conteúdo do índice Git**, incluindo
arquivos que serão commitados, sem seguir links simbólicos ou ler configuração local.
Bloqueia caminhos internos, referências ao ambiente de operação e segredos. A varredura
de segredos usa Gitleaks 8.24.3 (publicado em 11/04/2025), com imagem fixada por digest,
sem rede e com resultados ocultados por `--redact=100`. Requer Docker e Python 3.12.
O comando falha se não conseguir concluir a varredura. Arquivos não rastreados não
entram no commit nem são enviados ao scanner.

## Verificações antes do commit

```bash
uv sync --frozen --all-packages
uv run ruff check .
uv run ruff format --check .
uv run mypy packages apps/api
uv run pytest -q tests/unit

docker compose --profile test build tests
docker compose --profile test run --rm tests pytest -q

docker build -f infrastructure/docker/portal/Dockerfile --target test -t odb-portal-test .
docker run --rm odb-portal-test
```

Mudou a interface? Reconstrua a pilha local e rode Playwright pela imagem fixada no
projeto, inspecionando as capturas. Mudou o contrato? Regenere OpenAPI e os tipos do
portal e confira ambos no Git. Os testes não devem depender de fontes oficiais ao vivo.
Credenciais e dados de teste precisam ser locais ou efêmeros.
