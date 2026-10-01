#!/bin/bash
set -euo pipefail

source "$HOME/Jetson/.env.rrhh"

SRC="/tmp/rrhh_supabase_counts.txt"
LOC="/tmp/rrhh_local_counts.txt"

echo "Consultando Supabase..."

docker run --rm -i \
  -e PGPASSWORD="$SUPABASE_PASSWORD" \
  -e PGSSLMODE=require \
  postgres:17-alpine \
  psql \
    -h "$SUPABASE_HOST" \
    -p "$SUPABASE_PORT" \
    -U "$SUPABASE_USER" \
    -d "$SUPABASE_DB" \
    -At <<'SQL' | sort > "$SRC"
SELECT format(
    'SELECT %L || ''|'' || COUNT(*)::text FROM public.%I;',
    table_name,
    table_name
)
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
  AND table_name NOT IN (
    'recibos_sueldos',
    'viaticos',
    'viaticos_rendiciones',
    'viaticos_rendiciones_gastos',
    'adelantos',
    'mensajes',
    'solicitudes',
    'reservas_hotel'
  )
ORDER BY table_name;
\gexec
SQL

echo "Consultando Jetson..."

docker exec -i "$LOCAL_CONTAINER" \
  psql -U "$LOCAL_USER" -d "$LOCAL_DB" -At <<'SQL' | sort > "$LOC"
SELECT format(
    'SELECT %L || ''|'' || COUNT(*)::text FROM rrhh.%I;',
    table_name,
    table_name
)
FROM information_schema.tables
WHERE table_schema = 'rrhh'
  AND table_type = 'BASE TABLE'
  AND table_name NOT IN (
    'sync_info',
    'sync_tablas',
    'sync_eliminaciones'
  )
ORDER BY table_name;
\gexec
SQL

echo
echo "TABLA | SUPABASE | JETSON | ESTADO"
echo "--------------------------------------------"

join -t'|' -a1 -a2 -e "NO_EXISTE" \
  -o '0,1.2,2.2' \
  "$SRC" "$LOC" |
awk -F'|' '{
    estado = ($2 == $3 ? "OK" : "DIFERENTE")
    printf "%-30s | %-10s | %-10s | %s\n", $1, $2, $3, estado
}'
