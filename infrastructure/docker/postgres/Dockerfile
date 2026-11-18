# syntax=docker/dockerfile:1.7
# PostgreSQL da plataforma: a imagem oficial fixada por digest (ADR-0001) com os
# scripts de inicialização (papéis e bancos) copiados para dentro da imagem.
#
# Por que não um bind mount de ./infrastructure/postgres/init: no Docker Desktop
# com WSL2, os bind mounts de uma distro WSL só ficam disponíveis depois que a
# integração com a distro sobe. Quando o Docker Desktop reinicia (atualização,
# reinício do Windows), ele religa os contêineres com `restart: unless-stopped`
# antes disso; o mount falha ("no such file or directory"), o Docker não tenta de
# novo e a API fica sem catálogo. Os scripts só rodam com o volume de dados vazio,
# mas o mount é exigido em toda partida.
ARG POSTGRES_IMAGE=postgres:17-bookworm@sha256:839fbb5a4942a7758dd93e18b42ea5649807491a0545b5eeeb8f0b8bb11857a5
FROM ${POSTGRES_IMAGE}
COPY --chmod=0755 infrastructure/postgres/init/ /docker-entrypoint-initdb.d/
