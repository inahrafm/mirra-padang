// PM2 ecosystem file untuk Mirra Padang
// Jalankan dari dalam folder be-mirra-padang/:
//   pm2 start ecosystem.config.js
//
// Path venv dan frontend dihitung relatif terhadap lokasi file ini
// (__dirname), sehingga TIDAK perlu diedit setiap pindah VPS atau
// pindah lokasi clone repository.

const path = require("path");

const BACKEND_DIR = __dirname;
const FRONTEND_DIR = path.join(__dirname, "..", "fe-mirra-padang");
const VENV_PYTHON = path.join(BACKEND_DIR, "venv", "bin", "python");
const VENV_UVICORN = path.join(BACKEND_DIR, "venv", "bin", "uvicorn");

module.exports = {
  apps: [
    {
      name: "mirra-api",
      cwd: BACKEND_DIR,
      script: VENV_UVICORN,
      args: "api:app --host 0.0.0.0 --port 8888",
      interpreter: "none", // uvicorn sudah jadi executable dari venv
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "mirra-ingestion",
      cwd: BACKEND_DIR,
      script: "ingestion.py",
      interpreter: VENV_PYTHON,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "mirra-celery",
      cwd: BACKEND_DIR,
      script: "worker.py",
      interpreter: VENV_PYTHON,
      env: {
        PYTHONUNBUFFERED: "1",
      },
    },
    {
      name: "mirra-frontend",
      cwd: FRONTEND_DIR,
      script: "npm",
      args: "start",
    },
  ],
};
