from fastapi.responses import StreamingResponse
import io
import csv
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
from psycopg2.extras import RealDictCursor
import asyncio
from datetime import datetime
import json

app = FastAPI(title="DJKA Bridge Monitoring API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_DSN = "postgresql://djka_admin:djka_rahasia@127.0.0.1:5434/djka_monitoring"

def get_db_connection():
    return psycopg2.connect(DB_DSN)

@app.get("/")
def root():
    return {"status": "API Berjalan", "version": "1.0.0"}

# --- ENDPOINT REST ---
@app.get("/nodes")
def get_nodes():
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    cursor.execute("SELECT node_id, label, location, active FROM nodes ORDER BY node_id")
    nodes = cursor.fetchall()
    conn.close()
    return nodes

# --- ENDPOINT DIREVISI: Historis Cuaca dengan Downsampling ---
@app.get("/weather/history")
def get_weather_history(
    from_time: str = Query(..., description="Waktu mulai, format: YYYY-MM-DDTHH:MM:SS"),
    to_time: str = Query(..., description="Waktu selesai, format: YYYY-MM-DDTHH:MM:SS")
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Hitung selisih hari untuk menentukan ukuran keranjang (bucket)
        dt_from = datetime.fromisoformat(from_time)
        dt_to = datetime.fromisoformat(to_time)
        delta_days = (dt_to - dt_from).days

        if delta_days <= 1:
            bucket = '30 minutes'
        elif delta_days <= 7:
            bucket = '1 hour'
        else:
            bucket = '1 day'

        # Query Downsampling TimescaleDB
        # Catatan: Curah hujan menggunakan MAX karena nilainya kumulatif per hari
        cursor.execute(f"""
            SELECT 
                time_bucket('{bucket}', time) AS time,
                AVG(temperature) AS temperature,
                AVG(humidity) AS humidity,
                MAX(rainfall) AS rainfall,
                AVG(wind_speed) AS wind_speed
            FROM weather_readings 
            WHERE time >= %s AND time <= %s 
            GROUP BY 1 
            ORDER BY 1 ASC
        """, (from_time, to_time))
        
        history_data = cursor.fetchall()
        conn.close()
        
        # Bulatkan hasil desimal agar rapi dikirim ke frontend
        for row in history_data:
            if row['temperature']: row['temperature'] = round(row['temperature'], 2)
            if row['humidity']: row['humidity'] = round(row['humidity'], 2)
            if row['wind_speed']: row['wind_speed'] = round(row['wind_speed'], 2)

        return {
            "from": from_time,
            "to": to_time,
            "bucket_size": bucket,
            "total_records": len(history_data),
            "data": history_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

# --- ENDPOINT WEBSOCKET ---
@app.websocket("/ws/dashboard")
async def websocket_dashboard(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            conn = get_db_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("SELECT temperature, humidity, rainfall, wind_speed FROM weather_readings ORDER BY time DESC LIMIT 1")
            weather = cursor.fetchone()
            
            cursor.execute("""
                SELECT n.node_id, n.label, s.battery_v::FLOAT as battery_v, s.sd_ok,
                       f.dominant_hz, f.peak_magnitude
                FROM nodes n
                LEFT JOIN sessions s ON s.session_id = (
                    SELECT session_id FROM sessions WHERE node_id = n.node_id ORDER BY started_at DESC LIMIT 1
                )
                LEFT JOIN fft_results f ON f.session_id = s.session_id AND f.axis = 'ax' ORDER BY n.node_id
            """)
            nodes_status = cursor.fetchall()
            conn.close()

            await websocket.send_json({
                "weather": weather,
                "nodes": nodes_status
            })
            
            await asyncio.sleep(2)
            
    except WebSocketDisconnect:
        print("Frontend terputus dari WebSocket")
    except Exception as e:
        print("Error WebSocket:", e)

# --- ENDPOINT BARU: Export CSV Cuaca ---
@app.get("/weather/export")
def export_weather_csv(
    from_time: str = Query(..., description="Waktu mulai: YYYY-MM-DDTHH:MM:SS"),
    to_time: str = Query(..., description="Waktu selesai: YYYY-MM-DDTHH:MM:SS")
):
    try:
        conn = get_db_connection()
        cursor = conn.cursor() # Menggunakan cursor biasa agar mengambil data tuple
        
        cursor.execute("""
            SELECT time, gateway_id, temperature, humidity, rainfall, wind_speed 
            FROM weather_readings 
            WHERE time >= %s AND time <= %s 
            ORDER BY time ASC
        """, (from_time, to_time))
        
        rows = cursor.fetchall()
        conn.close()

        # Membuat struktur berkas CSV di dalam memori RAM
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Tulis Header Kolom CSV
        writer.writerow(["Timestamp (UTC)", "Gateway ID", "Suhu (C)", "Kelembaban (%RH)", "Curah Hujan (mm)", "Kecepatan Angin (m/s)"])
        
        # Tulis Data Baris demi Baris
        for row in rows:
            # Format waktu agar ramah dibaca di Excel
            waktu_terformat = row[0].strftime('%Y-%m-%d %H:%M:%S')
            writer.writerow([waktu_terformat, row[1], row[2], row[3], row[4], row[5]])
            
        output.seek(0)
        
        # Kembalikan sebagai File Downloadable
        filename = f"DJKA_Weather_Report_{from_time.split('T')[0]}.csv"
        return StreamingResponse(
            io.StringIO(output.read()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal generate CSV: {str(e)}")
    
# --- ENDPOINT BARU: Ambil Daftar Sesi dari Node Tertentu ---
@app.get("/nodes/{node_id}/sessions")
def get_node_sessions(node_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT session_id, started_at, sample_count, complete, battery_v::FLOAT, sd_ok, fft_done 
            FROM sessions 
            WHERE node_id = %s 
            ORDER BY started_at DESC LIMIT 20
        """, (node_id,))
        sessions = cursor.fetchall()
        conn.close()
        return sessions
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- PASTIKAN Endpoint FFT Lama Mengambil 'frequencies' dan 'magnitudes' ---
@app.get("/nodes/{node_id}/sessions/{session_id}/fft")
def get_fft_results(node_id: int, session_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("""
            SELECT axis, dominant_hz, peak_magnitude, frequencies, magnitudes 
            FROM fft_results 
            WHERE session_id = %s AND node_id = %s
        """, (session_id, node_id))

        results = cursor.fetchall()

        # safety convert kalau format postgres array masih string
        for row in results:
            if isinstance(row.get("frequencies"), str):
                row["frequencies"] = json.loads(row["frequencies"].replace("{", "[").replace("}", "]"))
            if isinstance(row.get("magnitudes"), str):
                row["magnitudes"] = json.loads(row["magnitudes"].replace("{", "[").replace("}", "]"))

        conn.close()
        return {"fft_data": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINT BARU: Export CSV Data Mentah Vibrasi per Sesi ---
@app.get("/nodes/{node_id}/sessions/{session_id}/export")
def export_node_session_csv(node_id: int, session_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor() # Menggunakan cursor biasa untuk performa fetch tuple
        
        # Ambil data akselerasi dan giroskop sekaligus
        cursor.execute("""
            SELECT time, ax, ay, az, gx, gy, gz 
            FROM vibration_raw 
            WHERE session_id = %s AND node_id = %s 
            ORDER BY time ASC
        """, (session_id, node_id))
        
        rows = cursor.fetchall()
        conn.close()

        if not rows:
            raise HTTPException(status_code=404, detail="Data mentah sesi tidak ditemukan")

        # Bangun file CSV di dalam memori RAM
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header mencakup seluruh 6 parameter sensor murni
        writer.writerow(["Timestamp", "ax (g)", "ay (g)", "az (g)", "gx (deg/s)", "gy (deg/s)", "gz (deg/s)"])
        
        for row in rows:
            # Pertahankan format milidetik (%f) karena ini data getaran berkecepatan tinggi
            waktu_terformat = row[0].strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            writer.writerow([waktu_terformat, row[1], row[2], row[3], row[4], row[5], row[6]])
            
        output.seek(0)
        
        filename = f"DJKA_Raw_Node_{node_id}_Session_{session_id}.csv"
        return StreamingResponse(
            io.StringIO(output.read()),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal ekspor data node: {str(e)}")
