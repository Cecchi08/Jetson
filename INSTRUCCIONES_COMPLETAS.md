# GUÍA COMPLETA DE INSTALACIÓN Y USO

## 1. Requisitos

- PostgreSQL 15+
- Node.js 20+
- Python 3.11+
- Ollama con modelo qwen2.5:14b-8k

## 2. Configuración de Base de Datos

### Crear la base de datos

```bash
# Conectarse a PostgreSQL
psql -U postgres

# Dentro de psql:
CREATE DATABASE orion;
\c orion
```

### Crear la tabla de usuarios

Ejecutar el SQL en [database/schema.sql](database/schema.sql):

```sql
CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
```

O desde la línea de comandos:

```bash
psql -U postgres -d orion -f database/schema.sql
```

## 3. Variables de Entorno

Copiar [.env.example](.env.example) a `.env`:

```bash
cp .env.example .env
```

Editar `.env` con los valores correctos:

```env
POSTGRES_HOST=localhost        # o 'postgres' si usas Docker
POSTGRES_PORT=5432
POSTGRES_DB=orion
POSTGRES_USER=postgres
POSTGRES_PASSWORD=123

BACKEND_PORT=3000
JWT_SECRET=cambiar_esto_por_un_secret_seguro
ORCHESTRATOR_URL=http://localhost:9080
ORCHESTRATOR_TIMEOUT=120000

GN_ID=1163
GN_USERNAME=pruebaapi
GN_PASSWORD=changeme
GN_API_BASE=https://api.gruponucleosa.com

OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=qwen2.5:14b-8k

HTTP_HOST=0.0.0.0
HTTP_PORT=9080
```

## 4. Instalación Manual (Sin Docker)

### 4.1 Orquestador Python

```bash
cd orquestrate

# Crear ambiente virtual
python -m venv .venv

# Activar ambiente
source .venv/bin/activate        # En Linux/Mac
# o
.venv\Scripts\activate           # En Windows

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python main.py
```

El orquestador estará en `http://localhost:9080`

### 4.2 Backend Node.js

```bash
cd backend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# O en producción
npm start
```

El backend estará en `http://localhost:3000`

### 4.3 Frontend

```bash
cd frontend

# Instalar dependencias
npm install

# Ejecutar en desarrollo
npm run dev

# O compilar para producción
npm run build
npm run preview
```

El frontend estará en `http://localhost:5173`

## 5. Flujo de Uso

### 5.1 Registrarse

```bash
curl -X POST http://localhost:3000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "miusuario",
    "password": "micontraseña123"
  }'
```

Respuesta:

```json
{
  "message": "Usuario registrado exitosamente",
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": 1,
    "username": "miusuario"
  }
}
```

### 5.2 Iniciar Sesión

```bash
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "miusuario",
    "password": "micontraseña123"
  }'
```

Respuesta igual que el registro.

### 5.3 Usar el Chat

Usar el token obtenido en `Authorization: Bearer <token>`:

```bash
curl -X POST http://localhost:3000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..." \
  -d '{
    "message": "Hola, ¿cómo estás?",
    "history": []
  }'
```

Respuesta:

```json
{
  "response": "Hola, estoy bien, gracias por preguntar. ¿En qué puedo ayudarte hoy?"
}
```

### 5.4 Frontend

1. Abrir `http://localhost:5173`
2. Ver pantalla de login
3. Registrarse o iniciar sesión
4. Acceder al chat
5. El historial se mantiene en la sesión
6. Cerrar sesión para salir

## 6. Con Docker Compose

```bash
# Crear .env si no existe
cp .env.example .env

# Editar .env con valores correctos

# Levantar todos los servicios
docker compose up -d --build

# Verificar que está todo corriendo
docker compose ps

# Ver logs
docker compose logs -f

# Parar todo
docker compose down
```

### Acceder a través de Docker

- Frontend: `http://localhost:8080` (vía Nginx)
- Backend: `http://localhost:3000` (directo)
- Orquestador: `http://localhost:9080` (directo)

## 7. Verificación

### 7.1 Health Check del Orquestador

```bash
curl http://localhost:9080/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

### 7.2 Base de Datos

Conectarse a PostgreSQL y verificar la tabla:

```bash
psql -U postgres -d orion

SELECT * FROM users;
```

### 7.3 Backend

```bash
curl http://localhost:3000/health
```

Respuesta:

```json
{"status":"ok"}
```

## 8. Notas Importantes

- **Contraseñas**: Almacenadas con hash bcrypt en PostgreSQL
- **Tokens**: JWT válidos por 24 horas
- **Historial**: Se mantiene en sesión del backend, no en BD
- **Sesión**: Al cerrar sesión se borra el historial
- **Auth**: Todo endpoint excepto `/api/auth/*` requiere JWT válido

## 9. Solución de Problemas

### Error: "No se puede conectar a PostgreSQL"

- Verificar que PostgreSQL esté corriendo
- Verificar valores en `.env`
- Verificar que la base de datos `orion` existe

### Error: "Orquestador no disponible"

- Verificar que Python está ejecutándose
- Verificar `ORCHESTRATOR_URL` en `.env`
- Ver logs del orquestador

### Error: "Token inválido"

- Token expiró (válido 24h)
- Token malformado
- Hacer login nuevamente

### El chat no responde

- Verificar que Ollama está corriendo
- Verificar que el modelo `qwen2.5:14b-8k` está descargado
- Ver logs del orquestador
