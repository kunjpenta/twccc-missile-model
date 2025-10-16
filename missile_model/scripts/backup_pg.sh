#!/bin/bash
set -e
BACKUP_DIR="/opt/missile_model/backups"
DB_NAME="missile_model_db"
DB_USER="postgres"

mkdir -p "$BACKUP_DIR"
DATE=$(date +%Y%m%d_%H%M%S)
FILE="$BACKUP_DIR/${DB_NAME}_$DATE.sql.gz"

echo "[INFO] Dumping database $DB_NAME..."
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILE"

# Keep 14 days
find "$BACKUP_DIR" -type f -mtime +14 -delete

echo "[INFO] Backup complete → $FILE"
