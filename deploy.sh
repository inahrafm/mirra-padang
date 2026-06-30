#!/usr/bin/env bash
# ============================================================
# MIRRA PADANG - Deploy Script (update existing deployment)
#
# Jalankan dari root repository:
#   ./deploy.sh
# ============================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/be-mirra-padang"
FRONTEND_DIR="$REPO_ROOT/fe-mirra-padang"

echo "==> Menarik perubahan terbaru"
cd "$REPO_ROOT"
git pull

# ------------------------------------------------------------
# Backend
# ------------------------------------------------------------
cd "$BACKEND_DIR"

echo "==> Update dependency Python"
./venv/bin/pip install -r requirements.txt

set -a
# shellcheck disable=SC1091
source .env
set +a

echo "==> Restart docker services"
docker compose down
docker compose up -d

echo "==> Menunggu TimescaleDB siap..."
until docker exec djka_db pg_isready -U "$DB_USER" >/dev/null 2>&1; do
    sleep 1
done

echo "==> Re-apply init.sql (idempotent, aman untuk schema yang sudah ada)"
PGPASSWORD="$DB_PASSWORD" psql \
    "postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}" \
    -f init.sql

# ------------------------------------------------------------
# Frontend
# ------------------------------------------------------------
cd "$FRONTEND_DIR"
echo "==> Update dependency frontend"
npm install

echo "==> Build frontend"
npm run build

# ------------------------------------------------------------
# Restart semua service PM2
# ------------------------------------------------------------
echo "==> Restart semua service PM2"
pm2 restart mirra-api mirra-ingestion mirra-celery mirra-frontend

echo ""
echo "==> Deploy selesai. Cek status: pm2 list"
