# Multi-stage build for production deployment.
# Stage 1: install dependencies and build the optimized static bundle.
FROM node:22-slim AS builder

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

RUN npm run build

# Stage 2: serve the built static files with a lightweight production server.
FROM node:22-slim

WORKDIR /app

RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 3000
CMD ["serve", "-s", "dist", "-l", "tcp://0.0.0.0:3000"]
