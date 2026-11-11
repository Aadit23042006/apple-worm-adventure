FROM node:22-alpine AS build

ARG VITE_GAME_NAME="APPLE WORM ADVENTURE"
ARG VITE_API_BASE_URL=/api

ENV VITE_GAME_NAME=${VITE_GAME_NAME}
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

WORKDIR /app

COPY package*.json ./

RUN npm ci --include=optional --no-audit --no-fund

RUN node -e "console.log('TypeScript:', require('typescript/package.json').version); console.log('Linux compiler package:', require.resolve('@typescript/typescript-linux-x64/package.json'))"

COPY . .

RUN npm run build

FROM nginx:1.27-alpine

RUN apk add --no-cache gettext

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/nginx.conf.template

ENV PORT=10000

EXPOSE 10000

CMD ["/bin/sh", "-c", ": \"${BACKEND_URL:?Set BACKEND_URL to the awa-backend Render URL}\"; : \"${PORT:=10000}\"; export PORT; envsubst '${PORT} ${BACKEND_URL}' < /etc/nginx/nginx.conf.template > /etc/nginx/conf.d/default.conf && exec nginx -g 'daemon off;'"]