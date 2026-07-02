FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runtime
RUN addgroup -S -g 1001 app && \
    adduser -S -u 1001 -G app app
WORKDIR /app
COPY --from=build /app/package.json ./package.json
COPY --from=build /app/next.config.js ./next.config.js
COPY --from=build /app/.next ./.next
COPY --from=build /app/node_modules ./node_modules
RUN chown -R app:app /app
EXPOSE 3000
USER app
ENV HOSTNAME=0.0.0.0
ENV NODE_ENV=production
CMD ["npm", "start"]
