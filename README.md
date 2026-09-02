# Orion Assistant - Arquitectura Final

Aplicación web con flujo:

React → Node.js/Express → Python Orquestador → Ollama/Qwen → Python → Node.js → React

## Requisitos

- Docker y Docker Compose
- Node.js 20 para desarrollo local
- Python 3.11 para el orquestador
- Ollama con el modelo `qwen2.5:14b-8k`
- PostgreSQL solo para autenticación, no para historial de chats

## Arquitectura

```
.
├── frontend/               # React + Vite + TypeScript
├── backend/                # Node.js + Express API
├── orquestrate/            # Python FastAPI orquestador
├── nginx/                  # Reverse proxy
├── database/               # Esquema auth / usuarios
├── docker-compose.yml
├── .env.example
├── .env
├── README.md
└── INICIO_RAPIDO.md
```

## Configuración

```bash
cp .env.example .env
```

Variables necesarias:

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=orion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123

BACKEND_PORT=3000
JWT_SECRET=change_this_secret
ORCHESTRATOR_URL=http://orchestrator:9080
ORCHESTRATOR_TIMEOUT=120000

GN_ID=1163
GN_USERNAME=pruebaapi
GN_PASSWORD=changeme
GN_API_BASE=https://api.gruponucleosa.com

OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:14b-8k

HTTP_HOST=0.0.0.0
HTTP_PORT=9080
```

> El historial de conversación se mantiene en memoria en el backend durante la sesión actual. No se persiste en PostgreSQL.

## Ejecutar manualmente

### 1) Orquestador Python

```bash
cd orquestrate
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

La API responde en:

```bash
http://localhost:9080/health
```

### 2) Backend Node

```bash
cd backend
npm install
npm run dev
```

El backend escucha en:

```bash
http://localhost:3000
```

### 3) Frontend

```bash
cd frontend
npm install
npm run dev
```

## Verificación HTTP

### Health del orquestador

```bash
curl http://localhost:9080/health
```

Debe devolver:

```json
{"status":"ok"}
```

### Chat con historial

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola",
    "history": []
  }'
```

Debe responder con un JSON tipo:

```json
{"response": "..."}
```

## PostgreSQL

La base de datos no guarda chats ni conversaciones. Solo debe existir la parte de autenticación y usuarios. La creación del esquema se hace manualmente por el usuario con SQL propio, sin asumir que la aplicación lo ejecute.

## Docker Compose

```bash
docker compose up -d --build
```

Los servicios son:

- frontend
- backend
- orchestrator
- ollama
- postgres
- nginx

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
