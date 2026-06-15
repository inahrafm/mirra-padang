import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime, timezone

# ================= Konfigurasi =================
MQTT_HOST = "127.0.0.1"
MQTT_PORT = 1883

# ================= Fungsi Helper =================
def generate_weather_payload():
    """Membuat dummy data cuaca sesuai spesifikasi gateway"""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "node_id": "gateway-01",
        "temperature": round(random.uniform(25.0, 32.0), 1),
        "humidity": round(random.uniform(60.0, 90.0), 1),
        "rainfall": round(random.uniform(0.0, 10.0), 2),
        "wind_speed": round(random.uniform(1.0, 5.0), 1)
    }

def generate_raw_csv_chunk(rows=100):
    """Membuat dummy data vibrasi (ax,ay,az,gx,gy,gz) format CSV"""
    lines = []
    # Header tidak dikirim sesuai spesifikasi, langsung data
    for _ in range(rows):
        ax = round(random.uniform(-0.5, 0.5) + 9.8, 4) # ax terpengaruh gravitasi
        ay = round(random.uniform(-0.5, 0.5), 4)
        az = round(random.uniform(-0.5, 0.5), 4)
        gx = round(random.uniform(-0.01, 0.01), 4)
        gy = round(random.uniform(-0.01, 0.01), 4)
        gz = round(random.uniform(-0.01, 0.01), 4)
        lines.append(f"{ax},{ay},{az},{gx},{gy},{gz}")
    return "\n".join(lines)

def generate_telemetry_payload(samples=3000):
    """Membuat dummy telemetry node"""
    return {
        "node_id": 1,
        "timestamp": int(time.time()),
        "battery_v": round(random.uniform(3.5, 4.2), 2),
        "samples": samples,
        "sd_status": "OK"
    }

# ================= Eksekusi Simulasi =================
#client = mqtt.Client("djka_simulator")
client = mqtt.Client(client_id="djka_simulator", protocol=mqtt.MQTTv311)
client.username_pw_set(username="mirra_admin", password="Mirra666") 
# client.username_pw_set("agpot", "agpot123") # Buka komen ini jika mosquitto-go-auth butuh auth

try:
    print(f"Menghubungkan ke MQTT Broker di {MQTT_HOST}:{MQTT_PORT}...")
    client.connect(MQTT_HOST, MQTT_PORT, 60)
    client.loop_start()

    # 1. Kirim Data Cuaca (Gateway)
    print("\n[1] Mengirim data Gateway (Cuaca)...")
    weather_data = generate_weather_payload()
    client.publish("djka/gateway", json.dumps(weather_data))
    print(f"    Terikirim: {weather_data}")
    time.sleep(2)

    # 2. Kirim Data Vibrasi Raw (Simulasi 1 Sesi = 30 chunk x 100 baris = 3000 sampel)
    print("\n[2] Mengirim data ESP32 Raw (Vibrasi)...")
    TOTAL_CHUNKS = 5 # Kita pakai 5 chunk saja (500 baris) agar demo cepat selesai
    
    for i in range(TOTAL_CHUNKS):
        csv_payload = generate_raw_csv_chunk(100)
        client.publish("djka/node1/raw", csv_payload)
        print(f"    Terkirim Chunk {i+1}/{TOTAL_CHUNKS} (100 baris)")
        time.sleep(0.5) # Jeda antar chunk

    # 3. Kirim Telemetry Node (Penanda akhir sesi)
    print("\n[3] Mengirim data Telemetry Node...")
    telemetry_data = generate_telemetry_payload(samples=TOTAL_CHUNKS * 100)
    client.publish("djka/node1/telemetry", json.dumps(telemetry_data))
    print(f"    Terkirim: {telemetry_data}")
    time.sleep(1)

    print("\n✅ Selesai. Simulasi pengiriman data berhasil.")

except Exception as e:
    print(f"❌ Terjadi kesalahan: {e}")
finally:
    client.loop_stop()
    client.disconnect()
