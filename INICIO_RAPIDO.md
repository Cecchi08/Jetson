# Inicio Rápido - Orion Assistant

## Requisitos

- Docker y Docker Compose
- Node.js 20
- Python 3.11
- Ollama corriendo localmente o en Docker
- PostgreSQL disponible para autenticación

## 1) Configurar variables

```bash
cp .env.example .env
nano .env
```

Usa valores similares a:

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

OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=qwen2.5:14b-8k
HTTP_HOST=0.0.0.0
HTTP_PORT=9080
```

## 2) Levantar servicios

```bash
docker compose up -d --build
```

## 3) Verificar orquestador

```bash
curl http://localhost:9080/health
```

Debe devolver:

```json
{"status":"ok"}
```

## 4) Verificar backend

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Hola",
    "history": []
  }'
```

## 5) Frontend

Abrir en el navegador:

```text
http://localhost:8080
```

## Nota importante

La base de datos no guarda conversaciones; la sesión existe solo en memoria del backend durante la conexión del usuario.
```

### 5.4 Chat Completo

1. Abre `http://IP_DE_LA_JETSON:8080`
2. Escribe: `Hola`
3. Presiona Enter
4. Deberías ver "Orion está pensando..."
5. Deberías recibir una respuesta de OpenClaw

Si funciona, ¡todo está bien! 🎉

## Troubleshooting

### El frontend no carga

```bash
# Ver logs
docker compose logs frontend

# Verificar que Nginx está funcionando
curl -v http://IP_DE_LA_JETSON:8080
```

### El backend no responde

```bash
# Ver logs
docker compose logs backend

# Verificar conexión a OpenClaw (desde la terminal de la Jetson)
curl -X POST http://OPENCLAW_URL/v1/chat/completions \
  -H "Authorization: Bearer OPENCLAW_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"Hola"}]}'
```

### PostgreSQL no está listo

```bash
# Ver logs de PostgreSQL
docker compose logs postgres

# Verificar que está sano
docker exec orion-postgres pg_isready
```

### No se puede conectar a la Jetson desde otro dispositivo

```bash
# Obtener IP de la Jetson
hostname -I

# Verificar que Nginx escucha en todas las interfaces
docker exec orion-nginx netstat -tlnp | grep 8080
```

## Detener el Proyecto

```bash
# Parar todo pero mantener datos
docker compose down

# Eliminar datos (cuidado)
docker compose down -v
```

## Ver Logs en Tiempo Real

```bash
# Todos los logs
docker compose logs -f

# Solo backend
docker compose logs -f backend

# Solo frontend
docker compose logs -f frontend

# Solo PostgreSQL
docker compose logs -f postgres
```

## Reconstruir Después de Cambios

Si modificas código en `frontend/src/` o `backend/src/`:

```bash
# Reconstruir
docker compose up -d --build

# Forzar reconstrucción sin cache
docker compose build --no-cache
docker compose up -d
```

## Conectarse a PostgreSQL Directamente

```bash
# Desde la Jetson
docker exec -it orion-postgres psql -U orion -d orion

# Desde otra máquina (si deseas exponer PostgreSQL)
psql -h IP_DE_LA_JETSON -U orion -d orion -W
```

## Información Útil

| Componente | Puerto | URL |
|-----------|--------|-----|
| Nginx (proxy) | 8080 | `http://IP:8080` |
| Frontend | 4173 | `http://IP:4173` (solo interno) |
| Backend | 3000 | `http://IP:3000` (solo interno) |
| PostgreSQL | 5432 | `postgresql://orion:pass@IP:5432/orion` |

## Contacto / Soporte

Si algo no funciona:

1. Verifica los logs: `docker compose logs`
2. Verifica el `.env`: `cat .env | grep -v PASSWORD`
3. Verifica OpenClaw: `curl http://OPENCLAW_URL/v1/models`
4. Verifica la conectividad: `ping IP_DE_LA_JETSON`

---

¡Listo para usar! 🚀
