# Mirra Padang

Sistem monitoring struktur jembatan berbasis IoT: data getaran (vibration), data cuaca, dan analisis FFT, dengan dashboard real-time.

---

# 1. Struktur Repository

```
mirra-padang/
├── README.md
├── setup.sh                  # Setup VPS baru (sekali jalan)
├── deploy.sh                 # Update deployment yang sudah ada
│
├── be-mirra-padang/
│   ├── api.py
│   ├── ingestion.py
│   ├── worker.py
│   ├── simulator.py
│   ├── simulator_loop.py
│   ├── init.sql               # Schema lengkap: 5 tabel + seed nodes
│   ├── requirements.txt
│   ├── docker-compose.yml
│   ├── ecosystem.config.js    # Konfigurasi PM2 untuk semua service
│   ├── .env.example
│   ├── docker/
│   │   └── mosquitto/
│   │       └── config/
│   │           ├── mosquitto.conf
│   │           └── pwfile.example
│   └── venv/                  # Dibuat otomatis oleh setup.sh
│
└── fe-mirra-padang/            # Aplikasi Next.js
```

Backend (`be-mirra-padang`) berisi FastAPI API, MQTT Ingestion, Celery Worker, Simulator, Docker Compose, dan database schema. Frontend (`fe-mirra-padang`) berisi aplikasi Next.js.

> Path venv dan service PM2 sudah tidak lagi bergantung pada lokasi absolut tertentu. `venv` selalu dibuat di dalam `be-mirra-padang/venv`, dan `ecosystem.config.js` membaca path tersebut secara relatif — sehingga **deployment di VPS baru tidak memerlukan penyesuaian path manual**.

---

# 2. Prerequisites

Sistem operasi yang disarankan: Ubuntu 22.04 atau lebih baru.

Install seluruh dependency.

```bash
sudo apt update

sudo apt install -y \
git \
python3 \
python3-pip \
python3-venv \
nodejs \
npm \
docker.io \
docker-compose-plugin
```

Install PM2.

```bash
sudo npm install -g pm2
```

Pastikan Docker berjalan.

```bash
sudo systemctl enable docker
sudo systemctl start docker
```

---

# 3. Clone Repository

```bash
git clone <REPOSITORY_URL>
cd mirra-padang
```

Pastikan struktur repository sesuai dengan poin nomor 1.

---

# 4. Setup VPS Baru

Seluruh proses setup (virtual environment, install dependency, `.env`, `pwfile`, menjalankan Docker, dan inisialisasi database) dilakukan melalui satu script.

```bash
chmod +x setup.sh deploy.sh
./setup.sh
```

Script ini akan berhenti sejenak setelah membuat `be-mirra-padang/.env` dari `.env.example` — **edit file tersebut terlebih dahulu** (isi password database dan kredensial MQTT) sebelum melanjutkan, lalu jalankan kembali `./setup.sh`.

`setup.sh` aman dijalankan berulang kali (idempotent): venv yang sudah ada tidak dibuat ulang, `.env` dan `pwfile` yang sudah ada tidak ditimpa, dan `init.sql` aman dieksekusi ulang tanpa merusak data yang sudah ada.

Yang dilakukan `setup.sh`:

1. Membuat virtual environment di `be-mirra-padang/venv` dan install dependency Python.
2. Membuat `be-mirra-padang/.env` dari `.env.example` (jika belum ada).
3. Membuat `pwfile` MQTT dari `pwfile.example` (jika belum ada).
4. Menjalankan `docker compose up -d` dan menunggu TimescaleDB siap.
5. Menjalankan `init.sql` (membuat seluruh tabel dan seed data node).
6. Install dependency dan build frontend.

---

# 5. Environment (.env)

Seluruh kredensial dan konfigurasi (database, Redis, MQTT, port API) terpusat di `be-mirra-padang/.env`, dibuat dari template `.env.example`.

```text
DB_HOST=127.0.0.1
DB_PORT=5434
DB_NAME=djka_monitoring
DB_USER=djka_admin
DB_PASSWORD=

REDIS_HOST=127.0.0.1
REDIS_PORT=6378

MQTT_HOST=127.0.0.1
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

API_PORT=8888
```

`docker-compose.yml` membaca nilai-nilai ini secara langsung, sehingga kredensial database tidak lagi tertulis langsung di file yang ikut di-commit ke git.

Jangan pernah melakukan commit terhadap file `.env`.

---

# 6. MQTT Password (pwfile)

Repository tidak menyimpan password MQTT asli. File `pwfile` dibuat otomatis oleh `setup.sh` dari `pwfile.example`. Apabila ingin menggunakan password berbeda, buat ulang file tersebut menggunakan `mosquitto_passwd`.

---

# 7. Verifikasi Docker & Database

Setelah `setup.sh` selesai, verifikasi seluruh container aktif.

```bash
docker ps
```

Minimal akan muncul: `djka_db`, `djka_redis`, `djka_mqtt`.

Verifikasi tabel database.

```bash
source be-mirra-padang/.env
psql "postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}" -c "\dt"
```

Minimal akan terbentuk: `nodes`, `sessions`, `vibration_raw`, `weather_readings`, `fft_results`.

Verifikasi seed node.

```bash
psql "postgresql://${DB_USER}@${DB_HOST}:${DB_PORT}/${DB_NAME}" -c "SELECT * FROM nodes;"
```

---

# 8. Menjalankan Seluruh Service (PM2)

Seluruh service backend dan frontend dikonfigurasi dalam satu file `ecosystem.config.js`, sehingga tidak perlu lagi menjalankan masing-masing service dengan path absolut secara manual.

```bash
cd be-mirra-padang
pm2 start ecosystem.config.js
```

Service yang dijalankan: `mirra-api` (Uvicorn), `mirra-ingestion` (MQTT ingestion), `mirra-celery` (worker FFT), `mirra-frontend` (Next.js).

Verifikasi.

```bash
pm2 list
curl http://127.0.0.1:8888/docs
```

Simpan konfigurasi PM2 agar service berjalan otomatis setelah reboot.

```bash
pm2 save
pm2 startup
```

Jalankan perintah yang ditampilkan oleh PM2, lalu simpan kembali.

```bash
pm2 save
```

---

# 9. Update Deployment

Untuk memperbarui deployment yang sudah berjalan (pull perubahan terbaru, update dependency, rebuild frontend, restart service):

```bash
./deploy.sh
```

Script ini menjalankan `git pull`, update dependency Python dan Node, restart Docker, menjalankan ulang `init.sql` (aman untuk schema yang sudah ada), build ulang frontend, lalu restart seluruh service PM2.

---

# 10. Troubleshooting

## API tidak dapat diakses

```bash
pm2 logs mirra-api
ss -tulpn | grep 8888
curl http://127.0.0.1:8888/docs
```

## Dashboard menunjukkan "Disconnected"

Periksa log backend (`pm2 logs mirra-api`), konfigurasi Nginx, dan koneksi WebSocket.

## Dashboard "Connected" tetapi cuaca kosong

```sql
SELECT * FROM weather_readings ORDER BY time DESC LIMIT 10;
```

Pastikan simulator atau gateway mengirim data.

## Dashboard tidak menampilkan Node

```sql
SELECT * FROM nodes;
SELECT * FROM sessions;
SELECT * FROM fft_results;
```

Apabila log ingestion menampilkan `violates foreign key constraint sessions_node_id_fkey`, berarti tabel `nodes` kosong — jalankan ulang `init.sql` (seed node sudah termasuk di dalamnya).

## Error: relation "weather_readings"/"fft_results" does not exist

Jalankan ulang `psql ... -f init.sql` dari dalam `be-mirra-padang/` — kedua tabel sudah termasuk dalam schema ini.

## Error: Connection refused (MQTT)

```bash
docker ps
docker compose logs
```

## Error: address already in use

```bash
ss -tulpn | grep 8888
```

## Error: No such file or directory (saat pm2 start)

Tidak akan terjadi lagi selama `venv` dibuat melalui `setup.sh` di lokasi standar (`be-mirra-padang/venv`), karena `ecosystem.config.js` mengambil path tersebut secara relatif. Apabila tetap muncul, pastikan `./setup.sh` sudah dijalankan dan `be-mirra-padang/venv` ada.

---

# 11. Nginx

Contoh konfigurasi reverse proxy.

```nginx
server {
    server_name mirra.indismart.co.id;

    location / {
        proxy_pass http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api/ {
        rewrite ^/api/(.*) /$1 break;
        proxy_pass http://127.0.0.1:8888;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

# 12. Struktur Database

Database menggunakan lima tabel utama, dibuat sekaligus oleh `init.sql`.

```text
nodes
   │
   └──────── sessions
                 │
                 ├──────── vibration_raw
                 │
                 └──────── fft_results

weather_readings
```

| Tabel | Fungsi |
|-------|--------|
| nodes | Master data node |
| sessions | Informasi setiap sesi pengiriman |
| vibration_raw | Data mentah accelerometer dan gyroscope |
| weather_readings | Data meteorologi |
| fft_results | Hasil FFT setiap sumbu |

---

# 13. Security

Repository **tidak boleh** menyimpan file berikut, dan keduanya sudah terdaftar di `.gitignore`:

```gitignore
.env
docker/mosquitto/config/pwfile
```

Gunakan password MQTT yang kuat, batasi akses PostgreSQL hanya untuk host yang diperlukan, dan gunakan HTTPS pada deployment production.

---

# 14. Deployment Checklist

**Persiapan**
- [ ] Install dependency (lihat bagian 2)
- [ ] Clone repository

**Setup**
- [ ] `chmod +x setup.sh deploy.sh`
- [ ] `./setup.sh` dijalankan, lalu `.env` sudah diisi
- [ ] `./setup.sh` dijalankan ulang hingga selesai tanpa error

**PM2**
- [ ] `pm2 start ecosystem.config.js` dari dalam `be-mirra-padang/`
- [ ] `pm2 save` dan `pm2 startup`

**Verifikasi**
- [ ] `curl http://127.0.0.1:8888/docs`
- [ ] Dashboard dapat diakses, status **Connected**
- [ ] Data cuaca, node, dan FFT tampil di dashboard

**Simulator (opsional, untuk pengujian)**
- [ ] Jalankan `simulator.py`
- [ ] Data cuaca masuk, session terbentuk, FFT berhasil dihitung
