# Production image for the ASIGNACION Angular app (UPDS dev stack, port 4213).
# Stage 1 builds the static bundle; stage 2 serves it with nginx, which also
# proxies /api to the FastAPI service so the app stays same-origin (no CORS).

FROM docker.io/library/node:24.20.0-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN npx ng build --configuration production

FROM docker.io/library/nginx:1.31.5-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/sistema-laboratorios/browser /usr/share/nginx/html
EXPOSE 4213
