import os
from dotenv import load_dotenv
load_dotenv()

import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime, timezone
from celery import Celery

# ================= Konfigurasi =================
celery_app = Celery('fft_tasks', broker=os.environ["CELERY_BROKER"])
DB_DSN = os.environ["DB_DSN"]
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

active_sessions = {}

try:
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = True
    cursor = conn.cursor()
    print("✅ Berhasil terhubung ke TimescaleDB")
except Exception as e:
    print(f"❌ Gagal koneksi DB: {e}")
    exit(1)

def on_connect(client, userdata, flags, reason_code, properties):
    if reason_code == 0:
        print("✅ Terhubung ke MQTT Broker")
        client.subscribe("djka/+/raw")
        client.subscribe("djka/+/telemetry")
        client.subscribe("djka/gateway")

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode('utf-8')
    
    # 1. Handler Cuaca
    if topic == "djka/gateway":
        try:
            data = json.loads(payload)
            waktu = data.get("timestamp") or datetime.now(timezone.utc)
            c = psycopg2.connect(DB_DSN)
            cur = c.cursor()
            cur.execute("""
                INSERT INTO weather_readings (time, gateway_id, temperature, humidity, rainfall, wind_speed)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (waktu, data.get("node_id"), data.get("temperature"), data.get("humidity"), data.get("rainfall"), data.get("wind_speed")))
            c.commit()
            print(f"🌦️  Data Cuaca tersimpan dari {data.get('node_id')} | waktu: {waktu}")
            c.close()
        except Exception as e:
            print(f"⚠️ Error cuaca: {e}")

    # 2. Handler Data Vibrasi (CSV RAW) - YANG SEBELUMNYA HILANG
    elif topic.endswith("/raw"):
        try:
            node_id = int(topic.split("/")[1].replace("node", ""))
            data = json.loads(payload)

            if node_id not in active_sessions:
                cursor.execute("""
                    INSERT INTO sessions (node_id, started_at)
                    VALUES (%s, %s) RETURNING session_id
                """, (node_id, datetime.now(timezone.utc)))
                session_id = cursor.fetchone()[0]
                active_sessions[node_id] = session_id
                print(f"🚀 Membuka Sesi Baru: ID {session_id} untuk Node {node_id}")
            else:
                session_id = active_sessions[node_id]

            waktu = datetime.now(timezone.utc)
            cursor.execute("""
                INSERT INTO vibration_raw (time, session_id, node_id, ax, ay, az, gx, gy, gz)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (waktu, session_id, node_id,
                data["ax"], data["ay"], data["az"],
                data["gx"], data["gy"], data["gz"]))
            print(f"📈 Tersimpan 1 baris vibrasi ke Sesi {session_id}")

        except Exception as e:
            print(f"⚠️ Error parsing raw: {e}")
    # 3. Handler Telemetry (Penutup Sesi & Pemicu Celery)
    elif topic.endswith("/telemetry"):
        try:
            node_id = int(topic.split("/")[1].replace("node", ""))
            data = json.loads(payload)
            
            if node_id in active_sessions:
                session_id = active_sessions[node_id]
                sample_count = data.get("samples", 0)
                is_complete = sample_count >= 3000
                
                cursor.execute("""
                    UPDATE sessions
                    SET sample_count = %s, complete = %s, battery_v = %s, sd_ok = %s
                    WHERE session_id = %s
                """, (sample_count, is_complete, data.get("battery_v"), data.get("sd_status") == "OK", session_id))
                
                print(f"🔋 Sesi {session_id} ditutup (Baterai: {data.get('battery_v')}V, Sampel: {sample_count})")
                
                # Triger FFT Worker
                print(f"📣 Mengirim perintah komputasi FFT untuk Sesi {session_id} ke Celery...")
                celery_app.send_task('tasks.compute_fft', args=[session_id])
                
                del active_sessions[node_id] 
        except Exception as e:
            print(f"⚠️ Error update telemetry: {e}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username=os.environ["MQTT_USERNAME"], password=os.environ["MQTT_PASSWORD"]) 
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)

print("🚀 Ingestion Service berjalan. Menunggu data...")
client.loop_forever()
