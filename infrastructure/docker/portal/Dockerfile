# syntax=docker/dockerfile:1.7
# Portal Next.js (Fase 5). Imagem fixada por digest (ADR-0001); Node 24 LTS.
ARG NODE_IMAGE=node:24.22.1-bookworm-slim@sha256:be8204d4bd327363357f532187b752ff62759c31bedf98e9e18fc08c9cbd605c

FROM ${NODE_IMAGE} AS deps
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY apps/portal/package.json apps/portal/package-lock.json ./
RUN --mount=type=cache,target=/root/.npm npm ci --no-audit --no-fund

FROM deps AS build
# Links do cabeçalho e do rodapé (DS v2.3). O Next embute NEXT_PUBLIC_* no build;
# sem valor, o link correspondente não aparece.
ARG NEXT_PUBLIC_CONTACT_URL=
ARG NEXT_PUBLIC_REPO_URL=
ARG NEXT_PUBLIC_INSTAGRAM_URL=
# Formas de doação da página /apoie (vazias = cartão oculto).
ARG NEXT_PUBLIC_APOIASE_URL=
ARG NEXT_PUBLIC_BMAC_URL=
ARG NEXT_PUBLIC_BMAC_QR=
ARG NEXT_PUBLIC_PIX_KEY=
ARG NEXT_PUBLIC_PIX_CODE=
ARG NEXT_PUBLIC_PIX_QR=
ARG NEXT_PUBLIC_BANK_NAME=
ARG NEXT_PUBLIC_BANK_RECIPIENT=
ARG NEXT_PUBLIC_BANK_BRANCH=
ARG NEXT_PUBLIC_BANK_OPERATION=
ARG NEXT_PUBLIC_BANK_ACCOUNT=
ENV NEXT_PUBLIC_CONTACT_URL=${NEXT_PUBLIC_CONTACT_URL} NEXT_PUBLIC_REPO_URL=${NEXT_PUBLIC_REPO_URL} \
    NEXT_PUBLIC_INSTAGRAM_URL=${NEXT_PUBLIC_INSTAGRAM_URL} NEXT_PUBLIC_APOIASE_URL=${NEXT_PUBLIC_APOIASE_URL} \
    NEXT_PUBLIC_BMAC_URL=${NEXT_PUBLIC_BMAC_URL} NEXT_PUBLIC_BMAC_QR=${NEXT_PUBLIC_BMAC_QR} \
    NEXT_PUBLIC_PIX_KEY=${NEXT_PUBLIC_PIX_KEY} NEXT_PUBLIC_PIX_CODE=${NEXT_PUBLIC_PIX_CODE} \
    NEXT_PUBLIC_PIX_QR=${NEXT_PUBLIC_PIX_QR}
ENV NEXT_PUBLIC_BANK_NAME=${NEXT_PUBLIC_BANK_NAME} NEXT_PUBLIC_BANK_RECIPIENT=${NEXT_PUBLIC_BANK_RECIPIENT} \
    NEXT_PUBLIC_BANK_BRANCH=${NEXT_PUBLIC_BANK_BRANCH} NEXT_PUBLIC_BANK_OPERATION=${NEXT_PUBLIC_BANK_OPERATION} \
    NEXT_PUBLIC_BANK_ACCOUNT=${NEXT_PUBLIC_BANK_ACCOUNT}
COPY apps/portal/ ./
RUN npm run build

# Testes do portal (tipos, lint e componentes), sem servidor.
FROM build AS test
CMD ["sh", "-c", "npx tsc --noEmit && npx eslint . && npx vitest run"]

FROM ${NODE_IMAGE} AS runtime
WORKDIR /app
# O servidor standalone só precisa do node: sem npm e corepack na imagem final, que
# traziam pacotes vulneráveis (undici, brace-expansion; varredura trivy da V6).
RUN rm -rf /usr/local/lib/node_modules/npm /usr/local/lib/node_modules/corepack \
    /usr/local/bin/npm /usr/local/bin/npx /usr/local/bin/corepack
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
COPY --from=build --chown=node:node /app/.next/standalone ./
COPY --from=build --chown=node:node /app/.next/static ./.next/static
# Arquivos estáticos (ex.: QR Codes da página Apoie, em public/apoie).
COPY --from=build --chown=node:node /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
