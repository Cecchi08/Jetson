@echo off
REM Script para inicializar la base de datos PostgreSQL en Windows

echo Iniciando PostgreSQL...
docker compose up -d postgres

echo Esperando a que PostgreSQL esté listo...
timeout /t 5 /nobreak

echo Creando esquema de base de datos...
docker exec -i orion-postgres psql -U orion -d orion < database\schema.sql

echo.
echo ✓ Base de datos inicializada exitosamente
echo.
echo Ahora puedes ejecutar:
echo   docker compose up -d --build
