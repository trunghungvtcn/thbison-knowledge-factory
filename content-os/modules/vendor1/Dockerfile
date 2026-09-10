# Reproducible Vendor 1 image. Non-root. Contract HTTP on 8080.
FROM node:22-bookworm-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev=false

FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:22-bookworm-slim
RUN useradd -m -u 10001 appuser
WORKDIR /app
COPY --from=build /app /app
ENV THBISON_MODE=MOCK
ENV THBISON_DATA_DIR=/app/data
USER 10001
EXPOSE 8080
HEALTHCHECK CMD node -e "fetch('http://127.0.0.1:8080/healthz').then(r=>process.exit(r.ok?0:1))"
CMD ["npm","run","dev"]
