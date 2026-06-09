#!/bin/sh
set -e

if [ -z "$1" ]; then
  echo "Usage: $0 <backup-file.tgz>"
  exit 1
fi

BACKUP_FILE=$1

echo "Stopping Elasticsearch container..."
docker-compose stop es01

docker run --rm \
  -v esdata01:/data \
  -v "$PWD":/backup \
  alpine sh -c "cd /data && tar xzf /backup/$BACKUP_FILE"

echo "Restore completed from: $PWD/$BACKUP_FILE"

docker-compose up -d es01
