"use client";

import { useEffect, useState } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

interface WeatherHistory {
  time: string;
  gateway_id: string;
  temperature: number;
  humidity: number;
  rainfall: number;
  wind_speed: number;
  formattedTime?: string;
}

export default function WeatherHistoryPage() {
  const [data, setData] = useState<WeatherHistory[]>([]);
  const [loading, setLoading] = useState(false);

  // Filter default: Hari ini
  const today = new Date().toISOString().split("T")[0];
  const [fromDate, setFromDate] = useState(today);
  const [toDate, setToDate] = useState(today);

  // State Pilihan Parameter (Default aktif: Suhu)
  const [showTemp, setShowTemp] = useState(true);
  const [showHum, setShowHum] = useState(false);
  const [showRain, setShowRain] = useState(false);
  const [showWind, setShowWind] = useState(false);

//  const API_BASE_URL = "http://103.197.189.18:8888";
const API_BASE_URL = "https://mirra.indismart.co.id/api";
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const fromTime = `${fromDate}T00:00:00`;
      const toTime = `${toDate}T23:59:59`;

      const res = await fetch(
        `${API_BASE_URL}/weather/history?from_time=${fromTime}&to_time=${toTime}`,
      );

      if (res.ok) {
        const json = await res.json();
        // PERUBAHAN DI SINI: Ganti "any" dengan "WeatherHistory"
        const formattedData = json.data.map((item: WeatherHistory) => {
          const dateObj = new Date(item.time);
          let timeLabel = "";

          if (json.bucket_size === "1 day") {
            timeLabel = dateObj.toLocaleDateString("id-ID", {
              day: "numeric",
              month: "short",
            });
          } else {
            timeLabel = dateObj.toLocaleString("id-ID", {
              day: json.bucket_size === "1 hour" ? "numeric" : undefined,
              month: json.bucket_size === "1 hour" ? "short" : undefined,
              hour: "2-digit",
              minute: "2-digit",
            });
          }

          return { ...item, formattedTime: timeLabel };
        });
        setData(formattedData);
      }
    } catch (error) {
      console.error("Gagal mengambil data historis", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    fetchHistory();
  }, []);

  const handleDownloadCSV = () => {
    const fromTime = `${fromDate}T00:00:00`;
    const toTime = `${toDate}T23:59:59`;
    window.open(
      `${API_BASE_URL}/weather/export?from_time=${fromTime}&to_time=${toTime}`,
      "_blank",
    );
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 min-h-screen bg-[#FAFAFA]">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">
          Historis Meteorologi
        </h1>
        <p className="text-sm text-gray-500 mt-1">
          Analisis perkembangan dan tren parameter cuaca makro jembatan
        </p>
      </div>

      {/* Panel Kontrol & Filter (Responsive Grid) */}
      <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] mb-6 flex flex-col md:flex-row md:items-end justify-between gap-6">
        {/* Date Inputs */}
        <div className="flex flex-wrap items-end gap-3">
          <div className="w-full sm:w-auto">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Mulai
            </label>
            <input
              type="date"
              value={fromDate}
              onChange={(e) => setFromDate(e.target.value)}
              className="w-full sm:w-auto border border-gray-200 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 text-gray-700"
            />
          </div>
          <div className="w-full sm:w-auto">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">
              Sampai
            </label>
            <input
              type="date"
              value={toDate}
              onChange={(e) => setToDate(e.target.value)}
              className="w-full sm:w-auto border border-gray-200 rounded-md px-3 py-1.5 text-sm focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 text-gray-700"
            />
          </div>
          <div className="flex gap-2 w-full sm:w-auto mt-2 sm:mt-0">
            <button
              onClick={fetchHistory}
              className="bg-gray-900 text-white px-4 py-1.5 rounded-md text-sm font-medium hover:bg-gray-800 transition-colors h-[34px]"
            >
              {loading ? "..." : "Filter"}
            </button>
            <button
              onClick={handleDownloadCSV}
              disabled={data.length === 0}
              className={`px-4 py-1.5 rounded-md text-sm font-medium border h-[34px] transition-colors ${
                data.length === 0
                  ? "border-gray-100 bg-gray-50 text-gray-300 cursor-not-allowed"
                  : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50"
              }`}
            >
              Unduh CSV
            </button>
          </div>
        </div>

        {/* Parameter Toggles */}
        <div className="flex flex-wrap gap-1.5 bg-gray-100/80 p-1 rounded-lg border border-gray-200">
          {[
            { label: "Suhu", state: showTemp, setState: setShowTemp },
            { label: "Kelembaban", state: showHum, setState: setShowHum },
            { label: "Hujan", state: showRain, setState: setShowRain },
            { label: "Angin", state: showWind, setState: setShowWind },
          ].map((btn) => (
            <button
              key={btn.label}
              onClick={() => btn.setState(!btn.state)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-all ${
                btn.state
                  ? "bg-white text-gray-900 shadow-sm border border-gray-200/50"
                  : "text-gray-500 hover:text-gray-900"
              }`}
            >
              {btn.label} {btn.state ? "✓" : ""}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content Area */}
      <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)]">
        {loading ? (
          <div className="h-80 w-full flex items-center justify-center text-sm text-gray-400">
            Sinkronisasi matriks tren cuaca...
          </div>
        ) : data.length === 0 ? (
          <div className="h-80 w-full flex items-center justify-center text-sm text-gray-400">
            Tidak ada data yang terekam pada interval waktu ini.
          </div>
        ) : (
          /* FIX RECHARTS ERROR: Menggunakan div berukuran absolut */
          <div
            className="w-full relative"
            style={{ height: "380px", minHeight: "380px" }}
          >
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data}>
                <CartesianGrid
                  strokeDasharray="3 3"
                  vertical={false}
                  stroke="#E5E7EB"
                />
                <XAxis
                  dataKey="formattedTime"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  dy={10}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fontSize: 11, fill: "#6B7280" }}
                  dx={-10}
                />
                <Tooltip
                  contentStyle={{
                    borderRadius: "8px",
                    border: "1px solid #E5E7EB",
                    boxShadow: "0 4px 6px -1px rgba(0,0,0,0.05)",
                    fontSize: "12px",
                  }}
                />
                <Legend
                  iconType="circle"
                  wrapperStyle={{ fontSize: "12px", paddingTop: "20px" }}
                />

                {showTemp && (
                  <Line
                    type="monotone"
                    name="Suhu Udara (°C)"
                    dataKey="temperature"
                    stroke="#DC2626"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
                {showHum && (
                  <Line
                    type="monotone"
                    name="Kelembaban (%RH)"
                    dataKey="humidity"
                    stroke="#2563EB"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
                {showRain && (
                  <Line
                    type="stepAfter"
                    name="Curah Hujan (mm)"
                    dataKey="rainfall"
                    stroke="#0891B2"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
                {showWind && (
                  <Line
                    type="monotone"
                    name="Kecepatan Angin (m/s)"
                    dataKey="wind_speed"
                    stroke="#7C3AED"
                    strokeWidth={2}
                    dot={false}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </main>
  );
}
