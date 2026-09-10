FROM node:22-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:22-bookworm-slim
RUN useradd --create-home --uid 10001 app
WORKDIR /app
COPY --from=build --chown=app:app /app /app
USER app
ENV CONTENT_OS_MODE=MOCK
ENV PORT=8080
EXPOSE 8080
CMD ["node", "scripts/with-app-env.mjs", "vite", "preview", "--host", "0.0.0.0", "--port", "8080"]
