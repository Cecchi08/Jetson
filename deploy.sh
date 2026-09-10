#!/bin/bash
set -e

# Paso 1: Asegurar que Docker este corriendo
echo "=== Step 1: Starting Docker ==="
sudo -S systemctl start docker 2>&1

# Paso 2: Reconstruir todas las imagenes con --no-cache
echo "=== Step 2: Building images with --no-cache ==="
cd /home/mateo/Jetson
docker-compose build --no-cache 2>&1

# Paso 3: Levantar los contenedores
echo "=== Step 3: Starting containers ==="
docker compose up -d 2>&1

# Paso 4: Verificar que todo esta corriendo
echo "=== Step 4: Checking status ==="
docker compose ps 2>&1
docker compose logs --tail=30 orchestrator 2>&1

echo "=== Deployment complete ==="