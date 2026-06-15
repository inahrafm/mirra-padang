import paho.mqtt.client as mqtt
import psycopg2
from psycopg2.extras import execute_values
import json
from datetime import datetime, timezone
from celery import Celery
import os
from dotenv import load_dotenv
load_dotenv()

# ================= Konfigurasi ================"
celery_app = Celery('fft_tasks', broker=os.environ["CELERY_BROKER"])
DB_DSN = os.environ["DB_DSN"]
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

active_sessions = {}


def get_conn():
    """Buat koneksi DB baru per operasi untuk menghindari koneksi zombie."""
    c = psycopg2.connect(DB_DSN)
    c.autocommit = False
    return c


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
            # Selalu pakai waktu server, abaikan timestamp payload
            # agar tidak kena unique constraint jika device kirim timestamp statis
            waktu = datetime.now(timezone.utc)
            c = get_conn()
            cur = c.cursor()
            cur.execute("""
                INSERT INTO weather_readings (time, gateway_id, temperature, humidity, rainfall, wind_speed)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                waktu,
                data.get("node_id"),
                data.get("temperature"),
                data.get("humidity"),
                data.get("rainfall"),
                data.get("wind_speed")
            ))
            c.commit()
            c.close()
            print(f"🌦️  Data Cuaca tersimpan dari {data.get('node_id')}")
        except Exception as e:
            print(f"⚠️ Error cuaca: {e}")

    # 2. Handler Data Vibrasi (CSV RAW - format multiline dari device)
    elif topic.endswith("/raw"):
        try:
            # Topic format: djka/node1/raw atau djka/1/raw
            node_str = topic.split("/")[1].replace("node", "")
            node_id = int(node_str)

            c = get_conn()
            cur = c.cursor()

            if node_id not in active_sessions:
                cur.execute("""
                    INSERT INTO sessions (node_id, started_at)
                    VALUES (%s, %s) RETURNING session_id
                """, (node_id, datetime.now(timezone.utc)))
                session_id = cur.fetchone()[0]
                c.commit()
                active_sessions[node_id] = session_id
                print(f"🚀 Membuka Sesi Baru: ID {session_id} untuk Node {node_id}")
            else:
                session_id = active_sessions[node_id]

            lines = payload.strip().split("\n")
            data_to_insert = []
            waktu = datetime.now(timezone.utc)

            for line in lines:
                # Lewati header jika ada
                if line.startswith("ax") or line.strip() == "":
                    continue
                cols = line.strip().split(",")
                if len(cols) == 6:
                    try:
                        ax, ay, az, gx, gy, gz = map(float, cols)
                        data_to_insert.append((waktu, session_id, node_id, ax, ay, az, gx, gy, gz))
                    except ValueError:
                        continue

            if data_to_insert:
                execute_values(cur, """
                    INSERT INTO vibration_raw (time, session_id, node_id, ax, ay, az, gx, gy, gz)
                    VALUES %s
                """, data_to_insert)
                c.commit()
                print(f"📈 Tersimpan {len(data_to_insert)} baris vibrasi ke Sesi {session_id}")

            c.close()

        except Exception as e:
            print(f"⚠️ Error parsing raw CSV: {e}")

    # 3. Handler Telemetry (Penutup Sesi & Pemicu Celery)
    # Firmware mengirim telemetry SETELAH semua raw data selesai dikirim
    elif topic.endswith("/telemetry"):
        try:
            node_str = topic.split("/")[1].replace("node", "")
            node_id = int(node_str)
            data = json.loads(payload)

            if node_id in active_sessions:
                session_id = active_sessions[node_id]
                sample_count = data.get("samples", 0)
                is_complete = sample_count >= 3000

                c = get_conn()
                cur = c.cursor()
                cur.execute("""
                    UPDATE sessions
                    SET sample_count = %s, complete = %s, battery_v = %s, sd_ok = %s
                    WHERE session_id = %s
                """, (
                    sample_count,
                    is_complete,
                    data.get("battery_v"),
                    data.get("sd_status") == "OK",
                    session_id
                ))
                c.commit()
                c.close()

                print(f"🔋 Sesi {session_id} ditutup (Baterai: {data.get('battery_v')}V, Sampel: {sample_count})")

                # Trigger FFT Worker setelah sesi ditutup
                print(f"📣 Mengirim perintah komputasi FFT untuk Sesi {session_id} ke Celery...")
                celery_app.send_task('tasks.compute_fft', args=[session_id])

                del active_sessions[node_id]
            else:
                print(f"⚠️ Telemetry diterima untuk Node {node_id} tapi tidak ada sesi aktif — kemungkinan raw belum masuk.")

        except Exception as e:
            print(f"⚠️ Error update telemetry: {e}")


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(username=os.environ["MQTT_USERNAME"], password=os.environ["MQTT_PASSWORD"])
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_HOST, MQTT_PORT, 60)

print("🚀 Ingestion Service berjalan. Menunggu data...")
client.loop_forever()
