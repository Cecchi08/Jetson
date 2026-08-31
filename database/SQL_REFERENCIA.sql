-- =============================================================
-- ORION ASSISTANT - SQL REFERENCIA COMPLETA
-- =============================================================

-- Tabla ÚNICA de autenticación y usuarios
-- NO hay tablas de chats, conversaciones, mensajes ni historial

-- =============================================================
-- CREAR TABLA DE USUARIOS
-- =============================================================

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  username VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índice para búsquedas rápidas
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

-- =============================================================
-- INSERTAR USUARIO DE PRUEBA
-- =============================================================

-- NOTA: Las contraseñas DEBEN estar hasheadas con bcrypt
-- Este ejemplo usa un hash bcrypt válido para demostración

-- Usuario: testuser
-- Contraseña: password123
-- Hash bcrypt: $2b$10$...

-- Para insertar un usuario con contraseña hasheada (desde la aplicación):
-- INSERT INTO users (username, password) VALUES ('testuser', '$2b$10$N9qo8uLOickgx2ZMRZoMyeIjZAgcg7b3XeKeUxWdeS86E36MM4YAu');

-- =============================================================
-- OPERACIONES COMUNES
-- =============================================================

-- Ver todos los usuarios
SELECT id, username, created_at FROM users;

-- Ver un usuario específico
SELECT * FROM users WHERE username = 'miusuario';

-- Contar usuarios
SELECT COUNT(*) FROM users;

-- Actualizar usuario
UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = 1;

-- Eliminar usuario
DELETE FROM users WHERE id = 1;

-- =============================================================
-- CONSULTAS DE VERIFICACIÓN
-- =============================================================

-- Verificar que la tabla existe
SELECT EXISTS (
  SELECT 1 FROM information_schema.tables 
  WHERE table_name = 'users'
);

-- Ver estructura de la tabla
\d users

-- Ver índices
SELECT * FROM pg_indexes WHERE tablename = 'users';

-- =============================================================
-- DATOS DE EJEMPLO COMPLETOS
-- =============================================================

-- Insertar usuario de ejemplo (NOTA: contraseña debe estar hasheada)
INSERT INTO users (username, password) VALUES 
('alice', '$2b$10$abcdef1234567890abcdef1234567890abcdef1234567890abc'),
('bob', '$2b$10$zyxwvu9876543210zyxwvu9876543210zyxwvu9876543210zyx');

-- Ver los usuarios creados
SELECT * FROM users;

-- =============================================================
-- INFORMACIÓN SOBRE HISTORIAL
-- =============================================================

/*
IMPORTANTE: El historial de conversaciones NO se almacena en la BD.

El flujo es:

1. Usuario inicia sesión (login) → obtiene JWT token
2. Frontend mantiene historial en localStorage
3. Cada mensaje enviado incluye el historial en payload
4. Backend procesa: message + history → Python orquestador
5. Orquestador genera respuesta
6. Frontend actualiza localStorage con respuesta
7. Al cerrar sesión: localStorage se borra

Razones:
- Las conversaciones son efímeras (solo sesión actual)
- No hay persistencia intencional
- Cada sesión es independiente
- Mejor performance sin almacenar millones de mensajes
*/

-- =============================================================
-- INTEGRIDAD Y CONSTRAINTS
-- =============================================================

-- USERNAME debe ser único (no puede haber dos usuarios con el mismo nombre)
ALTER TABLE users ADD CONSTRAINT unique_username UNIQUE (username);

-- PASSWORD no puede ser nulo
ALTER TABLE users ALTER COLUMN password SET NOT NULL;

-- USERNAME no puede ser nulo
ALTER TABLE users ALTER COLUMN username SET NOT NULL;

-- =============================================================
-- BACKUP Y RESTORE
-- =============================================================

-- Hacer backup de la tabla
pg_dump -U postgres -d orion -t users > users_backup.sql

-- Restaurar
psql -U postgres -d orion < users_backup.sql

-- =============================================================
-- LIMPIAR (CUIDADO: ELIMINA TODOS LOS USUARIOS)
-- =============================================================

-- DROP TABLE users;

-- =============================================================
-- CREAR DATABASE DESDE CERO
-- =============================================================

-- 1. Conectarse como postgres
psql -U postgres

-- 2. Crear la BD
CREATE DATABASE orion;

-- 3. Conectarse a la BD
\c orion

-- 4. Ejecutar el schema (copiar todo de arriba)
-- ... (ejecutar CREATE TABLE IF NOT EXISTS users ... )

-- 5. Verificar
SELECT * FROM users;
