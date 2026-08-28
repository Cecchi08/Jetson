FROM node:20-alpine AS build
WORKDIR /app
ARG VITE_OPENCLAW_URL
ARG VITE_OPENCLAW_TOKEN
ARG VITE_OPENCLAW_MODEL
ENV VITE_OPENCLAW_URL=$VITE_OPENCLAW_URL
ENV VITE_OPENCLAW_TOKEN=$VITE_OPENCLAW_TOKEN
ENV VITE_OPENCLAW_MODEL=$VITE_OPENCLAW_MODEL
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
