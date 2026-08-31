#!/bin/bash
# Script para inicializar la base de datos PostgreSQL

set -e

echo "Iniciando PostgreSQL..."
docker compose up -d postgres

echo "Esperando a que PostgreSQL esté listo..."
sleep 5

# Verificar que PostgreSQL está listo
max_attempts=30
attempt=0
until docker exec orion-postgres pg_isready -U "${POSTGRES_USER:-orion}" > /dev/null 2>&1; do
  if [ $attempt -ge $max_attempts ]; then
    echo "ERROR: PostgreSQL no está listo después de ${max_attempts} intentos"
    exit 1
  fi
  attempt=$((attempt + 1))
  echo "Intento $attempt/${max_attempts}: PostgreSQL aún no está listo..."
  sleep 1
done

echo "✓ PostgreSQL está listo"

echo "Creando esquema de base de datos..."
docker exec -i orion-postgres psql -U "${POSTGRES_USER:-orion}" -d "${POSTGRES_DB:-orion}" < database/schema.sql

echo "✓ Esquema de base de datos creado exitosamente"

echo ""
echo "Base de datos inicializada. Ahora puedes ejecutar:"
echo "  docker compose up -d --build"
