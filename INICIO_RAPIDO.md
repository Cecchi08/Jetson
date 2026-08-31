# Inicio Rápido - Orion Assistant Full Stack

## Requisitos Previos

- Docker y Docker Compose instalados en la Jetson
- OpenClaw ejecutándose en la Jetson (en algún puerto, ej: `http://172.15.0.202:18790`)
- Acceso a terminal/SSH en la Jetson

## Paso 1: Clonar o Descargar el Proyecto

```bash
# Asumiendo que ya estás en el directorio del proyecto
cd /ruta/al/proyecto
```

## Paso 2: Configurar Variables de Entorno

```bash
# Copiar plantilla
cp .env.example .env

# Editar con tus valores
nano .env
```

Valores necesarios:

```env
# OpenClaw (obtener del administrador)
OPENCLAW_URL=http://172.15.0.202:18790
OPENCLAW_TOKEN=tu_token_secreto_aqui
OPENCLAW_MODEL=openclaw

# PostgreSQL (cambiar contraseña)
POSTGRES_USER=orion
POSTGRES_PASSWORD=contraseña_muy_segura_aqui
POSTGRES_DB=orion

# Backend
BACKEND_PORT=3000
```

**⚠️ NO subir `.env` a Git**

## Paso 3: Inicializar PostgreSQL

```bash
# Levantar solo PostgreSQL
docker compose up -d postgres

# Esperar 10 segundos a que esté listo
sleep 10

# Crear schema
docker exec -i orion-postgres psql -U orion -d orion < database/schema.sql

# Verificar que funcionó
docker exec orion-postgres psql -U orion -d orion -c "SELECT * FROM pg_tables WHERE schemaname='public';"
```

Deberías ver:
```
           tablename           
-----------------------------
 messages
 conversations
```

## Paso 4: Levantar Todo (Frontend, Backend, Nginx)

```bash
# Construir e iniciar todos los servicios
docker compose up -d --build

# Verificar que está todo levantado
docker compose ps
```

Deberías ver:
```
NAME                COMMAND                  STATUS
orion-postgres      ...                      Up
orion-backend       npm start                Up
orion-frontend      npm run preview          Up
orion-nginx         nginx -g daemon off;     Up
```

## Paso 5: Verificar que Funciona

### 5.1 Frontend

Abre en el navegador:
```
http://IP_DE_LA_JETSON:8080
```

Deberías ver la interfaz de chat de Orion.

### 5.2 Backend

```bash
# Verificar que el backend responde
curl http://IP_DE_LA_JETSON:8080/api/health
```

Deberías ver:
```json
{"status":"ok"}
```

### 5.3 Base de Datos

```bash
# Conectarse a PostgreSQL
docker exec -it orion-postgres psql -U orion -d orion

# Dentro de psql:
SELECT COUNT(*) FROM conversations;
SELECT COUNT(*) FROM messages;
\q  # Salir
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
