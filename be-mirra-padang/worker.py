from celery import Celery
import psycopg2
import numpy as np
from datetime import datetime, timezone

# Konfigurasi Celery menggunakan Redis di port 6378 sesuai docker ps Anda
app = Celery('fft_tasks', broker='redis://127.0.0.1:6378/0')

DB_DSN = "postgresql://djka_admin:djka_rahasia@127.0.0.1:5434/djka_monitoring"

@app.task(name='tasks.compute_fft')
def compute_fft(session_id):
    print(f" Memulai perhitungan FFT untuk Sesi ID: {session_id}")
    
    try:
        # Koneksi ke database di dalam worker
        conn = psycopg2.connect(DB_DSN)
        conn.autocommit = True
        cursor = conn.cursor()
        
        # 1. Ambil data vibration_raw untuk sesi ini, urutkan berdasarkan waktu
        cursor.execute("""
            SELECT ax, ay, az, node_id FROM vibration_raw 
            WHERE session_id = %s 
            ORDER BY time ASC
        """, (session_id,))
        rows = cursor.fetchall()
        
        if not rows:
            print(f"❌ Tidak ada data vibrasi ditemukan untuk Sesi {session_id}")
            return False
            
        node_id = rows[0][3]
        
        # Konversi data ke format array Numpy untuk pemrosesan sinyal
        ax_signals = np.array([r[0] for r in rows])
        ay_signals = np.array([r[1] for r in rows])
        az_signals = np.array([r[2] for r in rows])
        
        n = len(ax_signals) # Jumlah sampel (misal 500 atau 3000)
        sample_rate = 100.0 # 100 Hz sesuai spesifikasi
        
        # Hitung distribusi frekuensi (X-axis)
        frequencies = np.fft.rfftfreq(n, d=1/sample_rate)
        
        # Proses untuk setiap sumbu (ax, ay, az)
        axes_data = {
            'ax': ax_signals,
            'ay': ay_signals,
            'az': az_signals
        }
        
        waktu_sekarang = datetime.now(timezone.utc)
        
        for axis_name, signal in axes_data.items():
            signal = signal - np.mean(signal)
            # Eksekusi Real FFT
            fft_complex = np.fft.rfft(signal)
            magnitudes = np.abs(fft_complex)  # nilai amplitudo

            # Cari frekuensi dominan (abaikan DC component index 0)
            if len(magnitudes) > 1:
                dominant_idx = np.argmax(magnitudes[1:]) + 1
                dominant_hz = float(frequencies[dominant_idx])
                peak_magnitude = float(magnitudes[dominant_idx])
            else:
                dominant_hz = 0.0
                peak_magnitude = 0.0

            # Simpan hasil FFT ke database
            cursor.execute("""
                INSERT INTO fft_results 
                (time, session_id, node_id, axis, frequencies, magnitudes, dominant_hz, peak_magnitude)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                waktu_sekarang,
                session_id,
                node_id,
                axis_name,
                frequencies.tolist(),
                magnitudes.tolist(),
                dominant_hz,
                peak_magnitude
            ))

        # Update status sessions setelah semua axis selesai
        cursor.execute("""
            UPDATE sessions 
            SET fft_done = TRUE 
            WHERE session_id = %s
        """, (session_id,))

        conn.commit()

        print(f"✅ FFT Berhasil dihitung untuk Sesi {session_id} (ax, ay, az)")

        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Gagal memproses FFT untuk Sesi {session_id}: {e}")
        return False
