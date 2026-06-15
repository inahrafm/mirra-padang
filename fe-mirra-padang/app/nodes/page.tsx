"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

interface SessionData {
  session_id: number;
  started_at: string;
  fft_done: boolean;
}

interface ChartPoint {
  hz: string;
  magnitude: number;
}

const formatDateToYMD = (dateString: string | Date) => {
  const d = new Date(dateString);
  const yyyy = d.getFullYear();
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  return `${yyyy}-${mm}-${dd}`;
};

function NodeContent() {
  const searchParams = useSearchParams();
  const initialNode = parseInt(searchParams.get("active") || "1");

  const [activeNode, setActiveNode] = useState<number>(initialNode);
  const [sessions, setSessions] = useState<SessionData[]>([]);
  const [selectedSession, setSelectedSession] = useState<number | null>(null);
  const [filterDate, setFilterDate] = useState<string>(formatDateToYMD(new Date()));
  const [activeAxis, setActiveAxis] = useState<string>("ax");
  const [chartData, setChartData] = useState<ChartPoint[]>([]);
  const [meta, setMeta] = useState({ dominant_hz: 0, peak_magnitude: 0 });

//  const API_BASE_URL = "http://103.197.189.18:8888";
  const API_BASE_URL = "https://mirra.indismart.co.id/api";
  useEffect(() => {
    async function fetchSessions() {
      try {
        const res = await fetch(`${API_BASE_URL}/nodes/${activeNode}/sessions`);
        if (res.ok) {
          const data = await res.json();
          setSessions(data);
        }
      } catch (error) {
        console.error("Fetch sessions error:", error);
      }
    }
    fetchSessions();
    const interval = setInterval(fetchSessions, 5000);
    return () => clearInterval(interval);
  }, [activeNode]);

  const filteredSessions = sessions.filter(s => formatDateToYMD(s.started_at) === filterDate);

  useEffect(() => {
    if (filteredSessions.length > 0 && !filteredSessions.find(s => s.session_id === selectedSession)) {
      setSelectedSession(filteredSessions[0].session_id);
    } else if (filteredSessions.length === 0) {
      setSelectedSession(null);
      setChartData([]);
    }
  }, [filterDate, filteredSessions.length, selectedSession]); 

  useEffect(() => {
    if (!selectedSession) return;
    const sessionDetail = sessions.find(s => s.session_id === selectedSession);
    if (sessionDetail && !sessionDetail.fft_done) {
      setChartData([]);
      return;
    }

    async function fetchFFT() {
      try {
        const res = await fetch(`${API_BASE_URL}/nodes/${activeNode}/sessions/${selectedSession}/fft`);
        if (res.ok) {
          const json = await res.json();
          // eslint-disable-next-line @typescript-eslint/no-explicit-any
          const axisData = json.fft_data?.find((item: any) => item.axis === activeAxis);
          if (axisData && axisData.frequencies) {
            setMeta({ dominant_hz: axisData.dominant_hz, peak_magnitude: axisData.peak_magnitude });
            const points = axisData.frequencies.map((freq: number, index: number) => ({
              hz: freq.toFixed(2),
              magnitude: axisData.magnitudes[index]
            }));
            setChartData(points.filter((_: unknown, idx: number) => idx % 2 === 0));
          } else {
            setChartData([]);
          }
        }
      } catch (error) {
         console.error("Fetch FFT error:", error);
      }
    }
    fetchFFT();
  }, [selectedSession, activeAxis, activeNode, sessions]);

  const handleDownloadRawCSV = () => {
    if (!selectedSession) return;
    window.open(`${API_BASE_URL}/nodes/${activeNode}/sessions/${selectedSession}/export`, "_blank");
  };

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 min-h-screen bg-[#FAFAFA]">
      <div className="flex space-x-1 bg-gray-100/80 p-1 rounded-lg w-max mb-8 border border-gray-200 shadow-sm">
        {[1, 2, 3, 4].map((num) => (
          <button
            key={num}
            onClick={() => setActiveNode(num)}
            className={`px-5 py-1.5 text-sm font-medium rounded-md transition-all ${
              activeNode === num 
                ? "bg-white text-gray-900 shadow-sm border border-gray-200/50" 
                : "text-gray-500 hover:text-gray-900"
            }`}
          >
            Node {num}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1 flex flex-col gap-4">
          <div className="bg-white border border-gray-200 rounded-xl p-4 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)]">
            <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Filter Tanggal</label>
            <input 
              type="date" 
              value={filterDate}
              onChange={(e) => setFilterDate(e.target.value)}
              className="w-full border border-gray-200 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-gray-900 focus:border-gray-900 transition-all text-gray-700"
            />
          </div>

          <div className="bg-white border border-gray-200 rounded-xl p-3 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] h-[450px] overflow-y-auto flex flex-col gap-1">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-2 py-2">Riwayat Sesi</h3>
            {filteredSessions.length === 0 ? (
              <div className="text-center text-sm text-gray-400 py-6">Tidak ada data.</div>
            ) : (
              filteredSessions.map((s) => (
                <button
                  key={s.session_id}
                  onClick={() => setSelectedSession(s.session_id)}
                  className={`w-full text-left px-3 py-2.5 rounded-md text-sm transition-all flex justify-between items-center ${
                    selectedSession === s.session_id 
                      ? "bg-gray-50 border border-gray-200 font-medium text-gray-900" 
                      : "border border-transparent text-gray-600 hover:bg-gray-50"
                  }`}
                >
                  <span>Sesi #{s.session_id}</span>
                  <span className="text-xs text-gray-400">
                    {new Date(s.started_at).toLocaleTimeString('id-ID', {hour:'2-digit', minute:'2-digit'})}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="lg:col-span-3">
          <div className="bg-white border border-gray-200 rounded-xl p-6 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)]">
            <div className="flex flex-col xl:flex-row justify-between xl:items-center mb-8 gap-6 border-b border-gray-100 pb-6">
              <div className="flex space-x-1 bg-gray-100/80 p-1 rounded-md border border-gray-200 w-max">
                {["ax", "ay", "az"].map((axis) => (
                  <button
                    key={axis}
                    onClick={() => setActiveAxis(axis)}
                    className={`px-4 py-1 text-xs font-medium rounded transition-all uppercase ${
                      activeAxis === axis ? "bg-white text-gray-900 shadow-sm" : "text-gray-500 hover:text-gray-900"
                    }`}
                  >
                    {axis}
                  </button>
                ))}
              </div>

              <div className="flex flex-wrap items-center gap-6">
                <div className="flex gap-6">
                  <div>
                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Frekuensi Dominan</p>
                    <p className="text-2xl font-semibold text-gray-900">{meta.dominant_hz.toFixed(2)} <span className="text-sm font-normal text-gray-500">Hz</span></p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-gray-500 uppercase tracking-wider">Amplitudo Puncak</p>
                    <p className="text-2xl font-semibold text-gray-900">{meta.peak_magnitude.toFixed(2)}</p>
                  </div>
                </div>

                <div className="hidden sm:block w-px h-8 bg-gray-200"></div>

                <button
                  onClick={handleDownloadRawCSV}
                  disabled={!selectedSession || chartData.length === 0}
                  className={`px-4 py-2 text-xs font-medium rounded-md border transition-all h-[36px] ${
                    !selectedSession || chartData.length === 0
                      ? "border-gray-200 bg-gray-50 text-gray-400 cursor-not-allowed"
                      : "border-gray-200 bg-white text-gray-700 hover:bg-gray-50 hover:text-gray-900 shadow-sm"
                  }`}
                >
                  Unduh CSV
                </button>
              </div>
            </div>

            <div className="w-full relative" style={{ height: "360px", minHeight: "360px" }}>
              {chartData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#E5E7EB" />
                    <XAxis dataKey="hz" tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} dy={10} />
                    <YAxis tick={{ fontSize: 12, fill: '#6B7280' }} axisLine={false} tickLine={false} dx={-10} />
                    <Tooltip 
                      contentStyle={{ borderRadius: '8px', border: '1px solid #E5E7EB', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)' }} 
                      itemStyle={{ color: '#111827', fontWeight: 500 }}
                    />
                    <Line type="monotone" dataKey="magnitude" stroke="#111827" strokeWidth={2} dot={false} activeDot={{ r: 4, fill: '#111827' }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="absolute inset-0 flex items-center justify-center text-gray-400 text-sm">
                  Pilih sesi untuk melihat data spektrum.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}

export default function NodePage() {
  return (
    <Suspense fallback={<div className="p-8 text-sm text-gray-500 text-center">Memuat...</div>}>
      <NodeContent />
    </Suspense>
  );
}
