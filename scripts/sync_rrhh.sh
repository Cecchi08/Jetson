#!/bin/bash
set -euo pipefail

source "$HOME/Jetson/.env.rrhh"

TMP="$HOME/Jetson/backups/rrhh_data.sql"
mkdir -p "$HOME/Jetson/backups"

echo "[$(date)] Exportando datos de Supabase..."

docker run --rm \
  -e PGPASSWORD="$SUPABASE_PASSWORD" \
  -e PGSSLMODE=require \
  postgres:17-alpine \
  pg_dump \
    -h "$SUPABASE_HOST" \
    -p "$SUPABASE_PORT" \
    -U "$SUPABASE_USER" \
    -d "$SUPABASE_DB" \
    --schema=public \
    --data-only \
    --no-owner \
    --no-privileges \
    --exclude-table=public.recibos_sueldos \
    --exclude-table=public.viaticos \
    --exclude-table=public.viaticos_rendiciones \
    --exclude-table=public.viaticos_rendiciones_gastos \
    --exclude-table=public.adelantos \
    --exclude-table=public.mensajes \
    --exclude-table=public.solicitudes \
    --exclude-table=public.reservas_hotel \
    > "$TMP"

echo "[$(date)] Vaciando datos locales..."

docker exec "$LOCAL_CONTAINER" \
  psql -U "$LOCAL_USER" -d "$LOCAL_DB" \
  -v ON_ERROR_STOP=1 \
  -c "
DO \$\$
DECLARE
    tablas TEXT;
BEGIN
    SELECT string_agg(format('%I.%I', schemaname, tablename), ', ')
    INTO tablas
    FROM pg_tables
    WHERE schemaname = 'rrhh'
      AND tablename NOT IN (
        'sync_info',
        'sync_tablas',
        'sync_eliminaciones'
      );

    IF tablas IS NOT NULL THEN
        EXECUTE 'TRUNCATE TABLE ' || tablas || ' RESTART IDENTITY CASCADE';
    END IF;
END
\$\$;
"

echo "[$(date)] Importando datos nuevos..."

sed \
  -e '/transaction_timeout/d' \
  -e '/pg_catalog.setval/d' \
  -e 's/public\./rrhh./g' \
  "$TMP" \
| docker exec -i "$LOCAL_CONTAINER" \
    psql -U "$LOCAL_USER" -d "$LOCAL_DB" \
    -v ON_ERROR_STOP=1

echo "[$(date)] RRHH sincronizado correctamente."
