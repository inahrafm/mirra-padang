# MIRRA Padang

Sistem monitoring IoT berbasis MQTT, FastAPI, Celery, TimescaleDB, Redis, dan Next.js.

## Struktur Repository

```
.
├── be-mirra-padang/
│   ├── api.py
│   ├── ingestion.py
│   ├── worker.py
│   ├── simulator.py
│   ├── simulator_loop.py
│   ├── requirements.txt
│   ├── docker-compose.yml
│   └── docker/
│       └── mosquitto/
│           ├── config/
│           │   ├── mosquitto.conf
│           │   └── pwfile.example
│           ├── data/
│           └── log/
│
└── fe-mirra-padang/
```

---

# Prerequisites

Ubuntu 22.04+ disarankan.

Install dependency:

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

Install PM2:

```bash
sudo npm install -g pm2
```

---

# Clone Repository

```bash
git clone <REPOSITORY_URL>

cd mirra-padang
```

---

# Backend Setup

Masuk ke backend.

```bash
cd be-mirra-padang
```

Buat Virtual Environment.

```bash
python3 -m venv venv

source venv/bin/activate
```

Install dependency.

```bash
pip install --upgrade pip

pip install -r requirements.txt
```

---

# Environment

Copy file environment.

```bash
cp .env.example .env
```

Sesuaikan isi `.env` dengan server yang digunakan.

---

# MQTT Password

Repository **tidak menyimpan password MQTT**.

Copy password file:

```bash
cp docker/mosquitto/config/pwfile.example \
   docker/mosquitto/config/pwfile
```

Atur permission:

```bash
chmod 644 docker/mosquitto/config/pwfile
```

---

# Start Infrastructure

Menjalankan:

* TimescaleDB
* Redis
* Mosquitto

```bash
docker compose up -d
```

Cek container:

```bash
docker ps
```

Harus muncul:

```
djka_db
djka_redis
djka_mqtt
```

---

# Frontend Setup

Masuk ke frontend.

```bash
cd ../fe-mirra-padang
```

Install dependency.

```bash
npm install
```

Build production.

```bash
npm run build
```

---

# Run with PM2

## Backend API

```bash
cd ../be-mirra-padang

source venv/bin/activate

pm2 start api.py \
    --name mirra-api \
    --interpreter ./venv/bin/python
```

---

## MQTT Ingestion

```bash
pm2 start ingestion.py \
    --name mirra-ingestion \
    --interpreter ./venv/bin/python
```

---

## Celery Worker

```bash
pm2 start worker.py \
    --name mirra-celery \
    --interpreter ./venv/bin/python
```

---

## Frontend

```bash
cd ../fe-mirra-padang

pm2 start npm \
    --name mirra-frontend \
    -- start
```

---

## Save PM2

```bash
pm2 save

pm2 startup
```

---

# Update Deployment

Masuk ke repository.

```bash
git pull
```

Backend.

```bash
cd be-mirra-padang

cp docker/mosquitto/config/pwfile.example \
   docker/mosquitto/config/pwfile

chmod 644 docker/mosquitto/config/pwfile

docker compose down

docker compose up -d
```

Frontend.

```bash
cd ../fe-mirra-padang

npm install

npm run build
```

Restart service.

```bash
pm2 restart mirra-api
pm2 restart mirra-ingestion
pm2 restart mirra-celery
pm2 restart mirra-frontend
```

---

# Useful Commands

Docker:

```bash
docker ps

docker compose logs

docker compose down

docker compose up -d
```

PM2:

```bash
pm2 list

pm2 logs

pm2 restart all

pm2 save
```

Git:

```bash
git status

git pull

git log --oneline
```

---

# Security

Repository **tidak menyimpan**:

* `.env`
* MQTT password (`pwfile`)

Jangan pernah commit file berikut:

```
.env
docker/mosquitto/config/pwfile
```
