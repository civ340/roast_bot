FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json .
# npm ci 完全照 package-lock.json 安裝，每次 build 拿到的相依套件版本才會一樣
RUN npm ci

COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
