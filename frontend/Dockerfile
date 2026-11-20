# syntax=docker/dockerfile:1
# ==============================================================================
# BizPulse Frontend - Production Multi-Stage Dockerfile
# ==============================================================================

# ------------------------------------------------------------------------------
# Stage 1: Build Static Assets
# ------------------------------------------------------------------------------
FROM node:22-alpine AS build

WORKDIR /app

# Copy package manifests for deterministic caching
COPY package.json package-lock.json* ./
RUN npm ci || npm install

# Build arguments for API Base URL (defaults to empty string for same-origin proxy)
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy TypeScript configuration and source files
COPY tsconfig*.json vite.config.ts index.html ./
COPY src/ ./src/

# Compile TypeScript and generate minified production bundle
RUN npm run build

# ------------------------------------------------------------------------------
# Stage 2: Serve Bundle with Hardened Nginx
# ------------------------------------------------------------------------------
FROM nginx:1.27-alpine AS serve

# Copy custom Nginx configuration with SPA routing and reverse proxy
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy compiled static assets from build stage
COPY --from=build /app/dist /usr/share/nginx/html

# Prepare pid and cache permissions for unprivileged execution
RUN touch /var/run/nginx.pid && \
    chown -R nginx:nginx /var/run/nginx.pid /usr/share/nginx/html /var/cache/nginx

EXPOSE 80

# Healthcheck verifying Nginx serves the root web application
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
