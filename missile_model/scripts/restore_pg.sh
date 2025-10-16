#!/bin/bash
set -e
DB_NAME="missile_model_db"
DB_USER="postgres"
FILE="$1"

if [ -z "$FILE" ]; then
  echo "Usage: restore_pg.sh <backupfile.sql.gz>"
  exit 1
fi

echo "[INFO] Restoring $FILE → $DB_NAME"
gunzip -c "$FILE" | psql -U "$DB_USER" "$DB_NAME"
echo "[INFO] Restore complete."
