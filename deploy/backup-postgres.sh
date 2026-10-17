#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="/var/backups/bigua"
STAMP="$(date +%Y-%m-%d_%H-%M-%S)"
mkdir -p "$BACKUP_DIR"
chown bigua:bigua "$BACKUP_DIR"

set -a
source /opt/bigua/src/.env
set +a

sudo -u bigua pg_dump --format=custom --file="$BACKUP_DIR/bigua-$STAMP.dump" "$DB_NAME"
find "$BACKUP_DIR" -type f -name 'bigua-*.dump' -mtime +14 -delete
