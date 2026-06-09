#!/usr/bin/env bash
# DB 전체를 SQL 덤프로 백업. 예: ./scripts/backup.sh  (또는 경로 지정)
set -euo pipefail

CONTAINER="${DB_CONTAINER:-prjmgmt-db-1}"
TS="$(date +%Y%m%d-%H%M%S)"
OUT="${1:-backups/prjmgmt-$TS.sql}"
mkdir -p "$(dirname "$OUT")"

docker exec "$CONTAINER" pg_dump -U prjmgmt -d prjmgmt > "$OUT"
echo "✓ 백업 저장: $OUT ($(du -h "$OUT" | cut -f1))"
