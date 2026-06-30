# Этап сборки: компиляция фронтенда в статические файлы
FROM node:20-alpine AS build
WORKDIR /app
COPY frontend/package.json ./
RUN npm install --no-audit --no-fund
COPY frontend/ .
RUN npm run build

# Этап выполнения: nginx раздаёт собранную статику и проксирует API
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
