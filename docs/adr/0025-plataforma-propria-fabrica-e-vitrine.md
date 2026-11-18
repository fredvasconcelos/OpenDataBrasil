# ADR-0025: Plataforma própria, separada em Fábrica e Vitrine

- **Estado:** aceito (2026-11-15), pelo mantenedor. A revisão de capacidade mostrou
  que o custo de construção e o armazenamento precisam ser separados da consulta pública.
- **Roteiro público:** [ROADMAP.md](../../ROADMAP.md).
- **Substitui:** a meta de migração para Azure Databricks ou Microsoft Fabric
  (CLAUDE.md §26, versão 1.1) e a obrigatoriedade do Delta Lake como formato da Gold.

## Contexto

O projeto não vai mais migrar para Databricks ou Fabric. O portal será publicado em
infraestrutura própria (VPS com datacenter no Brasil e domínio próprio), mantida por
financiamento coletivo. Os estouros de memória das rodadas 3 a 5 mostraram que o gargalo
está no modelo de dados (texto repetido por linha) e no build monolítico da Gold, não no
tamanho da máquina.

## Decisões

1. **Fábrica e Vitrine separadas.**
   - A Fábrica (máquina local) ingere, transforma, confere e empacota releases.
   - A Vitrine (servidor público) só serve releases prontos: proxy, portal, API, DuckDB
     somente leitura e catálogo PostgreSQL. Nunca transforma dados.
   - A Silver fica na Fábrica. A Vitrine recebe apenas a Gold do release aprovado.
2. **Formato do lakehouse por prova de conceito.** Delta Lake (atual), DuckLake e Parquet
   com manifesto serão medidos com os mesmos pilotos (5457, óbitos OB10, uma tabela
   compartilhada). Até a decisão, o Delta Lake continua sendo o formato oficial.
3. **Vitrine antecipada com o modelo atual.** O portal vai ao ar antes da reescrita da
   Fábrica. A Gold vigente tem 0,51 GB.
4. **Homologação no servidor doméstico antes de contratar a VPS.**
   - Ubuntu Server 24.04, 150 GB de disco.
   - Tudo deve ser reproduzido nele como seria na VPS: chaves SSH, firewall, implantação,
     migração da Gold e do catálogo, publicação, observabilidade, testes de carga e de
     segurança.
5. **CDN e túnel da Cloudflare (plano gratuito).** Serviço proprietário aceito pelo
   mantenedor. Ele fica na borda e é substituível pelo cache do Caddy. Os testes de carga
   rodam contra a origem na rede local, não pela borda.
6. **Stack de software sempre open source.** Serviços pagos só como infraestrutura comum
   e substituível (VPS, domínio).
7. **Bronze compactada sem perda (zstd)**, guardando o checksum do original e o do pacote,
   com recuperação conferida byte a byte. A execução acontece na etapa R2.
8. **Domínio:** `opendatabrasil.org`, a ser comprado na Hostinger (o `.org` não exige CNPJ).
   O DNS fica na Cloudflare.
9. **Observabilidade com OpenTelemetry:** traces e métricas da API (incluindo o tempo de
   cada consulta DuckDB) e do portal, com coletor e painéis open source.

## Consequências

- O CLAUDE.md passa à versão 2.0. Ele remove a meta de migração (§26), e onde o texto diz
  "Delta Lake" para a Gold, lê-se "o formato oficial do lakehouse" (hoje Delta).
- A implantação segue o [runbook genérico da Vitrine](../runbooks/vitrine.md), com
  homologação antes da publicação. Endereços e acessos pertencem à configuração de cada operador.
- A política de retenção Delta permanece pendente de decisão própria. A Vitrine recebe
  a versão publicada, e a Fábrica preserva os originais e o histórico necessário.
- **Licença (recomendação histórica, substituída pela [ADR-0028](0028-licencas-do-codigo-dos-textos-e-dos-dados.md)):** o código continua MIT, porque o
  repositório já é público sob MIT, e os dados derivados passam a CC BY 4.0, respeitando a
  licença de cada fonte.
