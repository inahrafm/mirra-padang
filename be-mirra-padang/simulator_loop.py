import paho.mqtt.client as mqtt
import json, time, random
from datetime import datetime, timezone

MQTT_HOST = "127.0.0.1"
MQTT_PORT = 8883

def generate_raw_csv_chunk(rows=100):
    lines = []
    for _ in range(rows):
        ax = round(random.uniform(-0.8, 0.8) + 9.8, 4)
        ay = round(random.uniform(-0.5, 0.5), 4)
        az = round(random.uniform(-0.5, 0.5), 4)
        gx, gy, gz = 0.01, 0.01, 0.01
        lines.append(f"{ax},{ay},{az},{gx},{gy},{gz}")
    return "\n".join(lines)

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.connect(MQTT_HOST, MQTT_PORT, 60)
client.loop_start()

nodes = [1, 2, 3, 4]
siklus = 1

print("🚀 Menjalankan Simulator Real-Time (4 Node)... Tekan Ctrl+C untuk berhenti.")

try:
    while True:
        print(f"\n--- Memulai Siklus Pengiriman ke-{siklus} ---")
        
        # 1. Kirim Data Cuaca (Fluktuatif)
        weather = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "node_id": "gateway-01",
            "temperature": round(random.uniform(25.0, 34.0), 1),
            "humidity": round(random.uniform(60.0, 95.0), 1),
            "rainfall": round(random.uniform(0.0, 15.0), 2),
            "wind_speed": round(random.uniform(1.0, 7.0), 1)
        }
        client.publish("djka/gateway", json.dumps(weather))
        
        # 2. Kirim Data Vibrasi & Telemetri per Node
        for n in nodes:
            # Kirim 3 chunk saja (300 baris) per node agar worker Celery tidak kepanasan
            for _ in range(3):
                client.publish(f"djka/node{n}/raw", generate_raw_csv_chunk(100))
                time.sleep(0.1)
                
            telemetry = {
                "node_id": n,
                "timestamp": int(time.time()),
                "battery_v": round(random.uniform(3.2, 4.2), 2), # Baterai fluktuatif
                "samples": 300,
                "sd_status": random.choice(["OK", "OK", "OK", "ERROR"]) # Simulasi error sesekali
            }
            client.publish(f"djka/node{n}/telemetry", json.dumps(telemetry))
            print(f"📡 Node {n} berhasil mengirim data sesi.")
            
        siklus += 1
        print("⏳ Menunggu 5 detik sebelum siklus berikutnya...")
        time.sleep(5)

except KeyboardInterrupt:
    print("\n🛑 Simulator dihentikan.")
    client.loop_stop()
    client.disconnect()
