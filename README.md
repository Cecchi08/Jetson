# Orion Assistant Frontend

Frontend experimental de un asistente empresarial, construido exclusivamente con React, TypeScript y Vite. Esta Fase 1 no incluye backend, APIs, autenticación, base de datos, OpenClaw, Ollama ni Qwen.

## Requisitos

- Node.js 20 o superior y npm
- Docker Engine y Docker Compose (para despliegue)
- En la Jetson: una imagen de Node/Docker compatible con su arquitectura

## Instalación y desarrollo

```bash
npm install
npm run dev
```

Vite escucha en `0.0.0.0:5173`, por lo que el desarrollo puede abrirse desde otro dispositivo en `http://IP-DE-LA-JETSON:5173`.

## Build de producción

```bash
npm run build
npm run preview
```

El build se genera en `dist/`. El preview escucha en `0.0.0.0:4173`.

## Docker

Construir e iniciar en segundo plano:

```bash
docker compose up -d --build
```

La aplicación queda publicada en el puerto `8080` del host. Desde otra computadora o celular de la misma red, abrir:

```text
http://IP-DE-LA-JETSON:8080
```

El servidor Nginx del contenedor escucha en `0.0.0.0` mediante el puerto `8080`, y Compose publica ese puerto hacia todas las interfaces del host.

## Obtener la IP de la Jetson

En Ubuntu/Linux:

```bash
hostname -I
```

También se puede consultar una interfaz concreta con:

```bash
ip addr
```

Usa la IP de la red local, no `127.0.0.1`.

## Operaciones frecuentes

Detener los contenedores:

```bash
docker compose down
```

Reconstruir después de cambios:

```bash
docker compose up -d --build
```

Ver logs:

```bash
docker compose logs -f
```

## Arquitectura

- `src/components/`: Sidebar, header, mensajes y composer.
- `src/hooks/useChat.ts`: estado de conversación, persistencia y streaming.
- `src/services/assistantService.ts`: contrato del servicio y simulación local reemplazable.
- `src/types/`: contratos TypeScript del dominio.

Las conversaciones se guardan en `localStorage` bajo la clave `orion-conversations`.
