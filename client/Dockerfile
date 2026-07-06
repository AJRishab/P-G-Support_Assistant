# -------------------------------------------------
#  Frontend – multi-stage build (node builder + nginx)
# -------------------------------------------------

# Stage 1: build static assets
FROM node:18-alpine AS builder

WORKDIR /app

# Copy package metadata first for layer caching
COPY client/package*.json ./
RUN npm install --legacy-peer-deps

# Copy the rest of the client source
COPY client/ ./

# Build production bundle (output: /app/dist)
RUN npm run build

# Stage 2: serve with nginx
FROM nginx:alpine

# Copy built assets from the builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Custom nginx config that proxies /api to the backend service
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Health-check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost/api/tickets || exit 1

CMD ["nginx", "-g", "daemon off;"]