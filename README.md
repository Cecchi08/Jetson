# Orion Assistant - Full Stack

Aplicación de chat con arquitectura completa: React, Express.js, PostgreSQL, Docker y OpenClaw.

## Requisitos

- Docker y Docker Compose
- Node.js 20 (opcional, solo para desarrollo local)
- OpenClaw ejecutándose en la Jetson

## Estructura del Proyecto

```
.
├── frontend/               # React + Vite + TypeScript
│   ├── src/
│   ├── package.json
│   ├── Dockerfile
│   └── ...
├── backend/                # Node.js + Express
│   ├── src/
│   │   ├── app.js
│   │   ├── index.js
│   │   ├── routes/
│   │   ├── controllers/
│   │   ├── services/
│   │   └── db/
│   ├── package.json
│   ├── Dockerfile
│   └── ...
├── nginx/                  # Reverse proxy
│   └── nginx.conf
├── database/               # Esquemas PostgreSQL
│   └── schema.sql
├── docker-compose.yml
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
```

## Configuración Inicial

### 1. Crear archivo .env

```bash
cp .env.example .env
```

Completar con valores reales:

```env
OPENCLAW_URL=http://172.15.0.202:18790
OPENCLAW_TOKEN=tu_token_aqui
OPENCLAW_MODEL=openclaw

POSTGRES_USER=orion
POSTGRES_PASSWORD=contraseña_segura_aqui
POSTGRES_DB=orion
BACKEND_PORT=3000
```

**IMPORTANTE**: No subir `.env` a Git ni exponerlo en Internet.

### 2. Crear la base de datos

Una vez que PostgreSQL está levantado dentro de Docker:

```bash
docker compose up -d postgres

# Esperar a que PostgreSQL esté listo
sleep 10

# Ejecutar el schema
docker exec -i orion-postgres psql -U orion -d orion < database/schema.sql
```

O usando psql localmente si está instalado:

```bash
PGPASSWORD=contraseña psql -h localhost -U orion -d orion -f database/schema.sql
```

## Ejecución

### Modo Desarrollo (Frontend)

```bash
cd frontend
npm install
npm run dev
```

Accedible en `http://localhost:5173`

### Modo Desarrollo (Backend)

```bash
cd backend
npm install
npm run dev
```

El backend escucha en `http://localhost:3000`

### Modo Producción (Docker Compose)

```bash
# Construir e iniciar todos los servicios
docker compose up -d --build

# Ver logs
docker compose logs -f
```

La aplicación estará disponible en:

```
http://IP_DE_LA_JETSON:8080
```

## Verificaciones

### 1. Frontend funciona

Acceder a:
```
http://IP_DE_LA_JETSON:8080
```

Debería ver la interfaz de chat.

### 2. Backend funciona

```bash
curl http://IP_DE_LA_JETSON:8080/api/health
```

Debería retornar:
```json
{"status":"ok"}
```

### 3. PostgreSQL funciona

```bash
docker exec orion-postgres psql -U orion -d orion -c "SELECT version();"
```

### 4. Backend puede conectarse a PostgreSQL

```bash
docker compose logs backend
```

No debería haber errores de conexión.

### 5. Backend puede conectarse a OpenClaw

```bash
curl -X POST http://IP_DE_LA_JETSON:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "Hola"}
    ]
  }'
```

Debería retornar una respuesta de OpenClaw.

### 6. Chat completo funciona

1. Abrir `http://IP_DE_LA_JETSON:8080` en el navegador
2. Escribir un mensaje
3. Presionar Enter
4. Debería ver un indicador "Orion está pensando"
5. Debería recibir una respuesta de OpenClaw

## Operaciones Comunes

### Detener servicios

```bash
docker compose down
```

### Reconstruir después de cambios

```bash
docker compose up -d --build
```

### Ver logs en tiempo real

```bash
docker compose logs -f
```

### Limpiar todo (incluyendo volumen de PostgreSQL)

```bash
docker compose down -v
```

### Conectarse a PostgreSQL

```bash
docker exec -it orion-postgres psql -U orion -d orion
```

## Arquitectura

```
Navegador
    ↓
Nginx (8080)
    ├─→ / → Frontend (4173)
    └─→ /api/ → Backend (3000)
        ├→ PostgreSQL (5432)
        └→ OpenClaw (18790)
             ↓
           Ollama
             ↓
            Qwen
```

## Seguridad

- El token de OpenClaw está en `.env` (no se expone al navegador)
- La contraseña de PostgreSQL está en `.env`
- Frontend y Backend se comunican a través de Nginx (mismo origen)
- No se guarda información sensible en localStorage (solo conversaciones)

## Problemas Frecuentes

**Backend no puede conectarse a OpenClaw:**
- Verificar que OpenClaw esté ejecutándose en la Jetson
- Verificar que `OPENCLAW_URL` sea correcta
- Verificar que `OPENCLAW_TOKEN` sea válido

**Frontend no recibe respuestas:**
- Verificar que Backend esté ejecutándose: `docker compose logs backend`
- Verificar que PostgreSQL esté sano: `docker compose logs postgres`

**Docker Compose versión antigua:**
Si tienes Docker Compose 1.x, reemplaza `docker compose` con `docker-compose`:

```bash
docker-compose up -d --build
```

## Tecnologías

- **Frontend**: React 18 + Vite + TypeScript + Lucide Icons
- **Backend**: Node.js 20 + Express.js
- **Base de Datos**: PostgreSQL 15
- **Reverse Proxy**: Nginx 1.27
- **Contenedores**: Docker + Docker Compose
- **IA**: OpenClaw + Ollama + Qwen

## Licencia

Uso interno.
