# Dev-only for now (Section 21: "frontend (Vite dev server)") — no
# prod/nginx stage yet, since there's no deployment target defined for
# it beyond local Docker Compose.
FROM node:22-slim

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
