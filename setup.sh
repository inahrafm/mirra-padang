#!/usr/bin/env bash
# ============================================================
# MIRRA PADANG - Setup Script (VPS baru / first-time setup)
#
# Jalankan dari root repository:
#   ./setup.sh
#
# Script ini idempotent: aman dijalankan ulang.
# Menggantikan langkah manual setup venv, .env, pwfile,
# docker up, dan init database.
# ============================================================

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$REPO_ROOT/be-mirra-padang"
FRONTEND_DIR="$REPO_ROOT/fe-mirra-padang"

echo "==> Mirra Padang setup dimulai di: $REPO_ROOT"

# ------------------------------------------------------------
# 1. Backend: virtual environment
# ------------------------------------------------------------
cd "$BACKEND_DIR"

if [ ! -d "venv" ]; then
    echo "==> Membuat virtual environment di be-mirra-padang/venv"
    python3 -m venv venv
else
    echo "==> venv sudah ada, lewati pembuatan"
fi

echo "==> Install/upgrade dependency Python"
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# ------------------------------------------------------------
# 2. Backend: .env
# ------------------------------------------------------------
if [ ! -f ".env" ]; then
    echo "==> Membuat .env dari .env.example"
    cp .env.example .env
    echo "    PENTING: edit be-mirra-padang/.env sebelum lanjut (password, dsb)"
else
    echo "==> .env sudah ada, lewati"
fi

# ------------------------------------------------------------
# 3. Backend: MQTT pwfile
# ------------------------------------------------------------
if [ ! -f "docker/mosquitto/config/pwfile" ]; then
    echo "==> Membuat pwfile dari pwfile.example"
    cp docker/mosquitto/config/pwfile.example docker/mosquitto/config/pwfile
    chmod 644 docker/mosquitto/config/pwfile
else
    echo "==> pwfile sudah ada, lewati"
fi

# ------------------------------------------------------------
# 4. Load .env supaya bisa dipakai untuk docker compose & psql
# ------------------------------------------------------------
set -a
# shellcheck disable=SC1091
source .env
set +a

# ------------------------------------------------------------
# 5. Docker services
# ------------------------------------------------------------
echo "==> Menjalankan docker compose up -d"
docker compose up -d

echo "==> Menunggu TimescaleDB siap..."
until docker exec djka_db pg_isready -U "$DB_USER" >/dev/null 2>&1; do
    sleep 1
done
echo "    TimescaleDB siap."

# ------------------------------------------------------------
# 6. Inisialisasi database (init.sql sudah idempotent)
# ------------------------------------------------------------
echo "==> Menjalankan init.sql"
PGPASSWORD="$DB_PASSWORD" psql \
    "postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}" \
    -f init.sql

# ------------------------------------------------------------
# 7. Frontend
# ------------------------------------------------------------
echo "==> Install dependency frontend"
cd "$FRONTEND_DIR"
npm install

echo "==> Build frontend"
npm run build

echo ""
echo "============================================================"
echo " Setup selesai."
echo ""
echo " Langkah berikutnya:"
echo "   cd be-mirra-padang"
echo "   pm2 start ecosystem.config.js"
echo "   pm2 save"
echo "============================================================"
