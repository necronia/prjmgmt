# Frontend — Vite build → Caddy 정적 서빙 (+ /api 리버스 프록시)
FROM node:20-alpine AS builder
WORKDIR /build
COPY package.json package-lock.json* ./
RUN npm install --no-audit --no-fund
COPY . .
RUN npm run build

FROM caddy:2-alpine
COPY --from=builder /build/dist /srv
COPY Caddyfile /etc/caddy/Caddyfile
EXPOSE 80
