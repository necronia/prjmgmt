#!/usr/bin/env bash
# 백업 SQL 덤프를 현재 DB에 복원. 예: ./scripts/restore.sh backups/prjmgmt-XXXX.sql
set -euo pipefail

CONTAINER="${DB_CONTAINER:-prjmgmt-db-1}"
IN="${1:?복원할 .sql 파일 경로를 지정하세요}"

[ -f "$IN" ] || { echo "파일 없음: $IN" >&2; exit 1; }
docker exec -i "$CONTAINER" psql -U prjmgmt -d prjmgmt < "$IN"
echo "✓ 복원 완료: $IN"
