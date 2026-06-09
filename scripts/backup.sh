#!/bin/sh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tgz>"
  exit 1
fi

BACKUP_FILE=$1

docker run --rm \
  -v esdata01:/data \
  -v "$PWD":/backup \
  alpine sh -c "cd /data && tar czf /backup/$BACKUP_FILE ."

echo "Backup completed: $PWD/$BACKUP_FILE"
