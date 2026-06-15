"use client";

import { useEffect, useState } from "react";
import Link from "next/link";

// Definisikan bentuk tipe data
interface WeatherData {
  temperature: number | null;
  humidity: number | null;
  rainfall: number | null;
  wind_speed: number | null;
}

interface NodeData {
  node_id: number;
  label: string;
  battery_v: number;
  sd_ok: boolean;
  dominant_hz: number | null;
  peak_magnitude: number | null;
}

export default function Dashboard() {
  const [weather, setWeather] = useState<WeatherData | null>(null);
  const [nodes, setNodes] = useState<NodeData[]>([]);
  const [status, setStatus] = useState("Connecting...");

//  const API_IP = "103.197.189.18:8888";
  const API_DOMAIN = "mirra.indismart.co.id";

//  const API_IP = "https://mirra.indismart.co.id/api/";

  useEffect(() => {
  //  const ws = new WebSocket(`ws://${API_IP}/ws/dashboard`);
 //  const ws = new WebSocket(`wss://${API_DOMAIN}/ws/dashboard`); 
const ws = new WebSocket(`wss://${API_DOMAIN}/api/ws/dashboard`);  
 ws.onopen = () => setStatus("Connected");
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setWeather(data.weather);
      setNodes(data.nodes);
    };
    ws.onclose = () => setStatus("Disconnected");
    return () => ws.close();
  }, []);

  return (
    <main className="mx-auto max-w-7xl px-6 py-8 min-h-screen bg-[#FAFAFA]">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900 tracking-tight">System Overview</h1>
          <p className="text-sm text-gray-500 mt-1">Pemantauan infrastruktur jembatan real-time</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="relative flex h-2.5 w-2.5">
            {status === "Connected" && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
            <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${status === "Connected" ? "bg-green-500" : "bg-red-500"}`}></span>
          </span>
          <span className="text-sm font-medium text-gray-600">{status}</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        <div className="lg:col-span-1">
          <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] h-full flex flex-col">
            <div className="flex justify-between items-center mb-6">
              <h2 className="text-sm font-semibold text-gray-900">Meteorologi</h2>
              <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-gray-100 text-gray-600 border border-gray-200">LIVE</span>
            </div>
            
            <div className="flex flex-col gap-4 flex-grow">
              <div className="flex justify-between items-end border-b border-gray-100 pb-2">
                <span className="text-xs text-gray-500 font-medium">Suhu Udara</span>
                <span className="text-lg font-semibold text-gray-900">{weather?.temperature ?? "--"}<span className="text-sm text-gray-500 font-normal">°C</span></span>
              </div>
              <div className="flex justify-between items-end border-b border-gray-100 pb-2">
                <span className="text-xs text-gray-500 font-medium">Kelembaban</span>
                <span className="text-lg font-semibold text-gray-900">{weather?.humidity ?? "--"}<span className="text-sm text-gray-500 font-normal">%</span></span>
              </div>
              <div className="flex justify-between items-end border-b border-gray-100 pb-2">
                <span className="text-xs text-gray-500 font-medium">Curah Hujan</span>
                <span className="text-lg font-semibold text-gray-900">{weather?.rainfall ?? "--"}<span className="text-sm text-gray-500 font-normal">mm</span></span>
              </div>
              <div className="flex justify-between items-end">
                <span className="text-xs text-gray-500 font-medium">Angin</span>
                <span className="text-lg font-semibold text-gray-900">{weather?.wind_speed ?? "--"}<span className="text-sm text-gray-500 font-normal">m/s</span></span>
              </div>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-5">
          {nodes.map((node) => (
            <Link href={`/nodes?active=${node.node_id}`} key={node.node_id} className="block group">
              <div className="bg-white border border-gray-200 rounded-xl p-5 shadow-[0_2px_8px_-4px_rgba(0,0,0,0.05)] group-hover:border-gray-400 transition-all duration-200 h-full flex flex-col justify-between">
                <div>
                  <div className="flex justify-between items-center mb-6">
                    <h3 className="font-semibold text-gray-900">{node.label}</h3>
                    <div className="flex gap-2">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${node.battery_v < 3.3 ? 'bg-orange-50 text-orange-700 border-orange-200' : 'bg-gray-50 text-gray-600 border-gray-200'}`}>
                        {node.battery_v?.toFixed(2)}V
                      </span>
                      <span className={`px-2 py-0.5 rounded text-[10px] font-medium border ${node.sd_ok ? 'bg-green-50 text-green-700 border-green-200' : 'bg-red-50 text-red-700 border-red-200'}`}>
                        SD: {node.sd_ok ? 'OK' : 'ERR'}
                      </span>
                    </div>
                  </div>
                  
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Dominan Hz</p>
                      <p className="text-2xl font-semibold text-gray-900">{node.dominant_hz?.toFixed(2) || "0.00"}</p>
                    </div>
                    <div>
                      <p className="text-[11px] font-medium text-gray-500 uppercase tracking-wider mb-1">Amplitudo</p>
                      <p className="text-2xl font-semibold text-gray-900">{node.peak_magnitude?.toFixed(2) || "0.00"}</p>
                    </div>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-gray-100 flex justify-between items-center text-xs text-gray-500 font-medium group-hover:text-gray-900 transition-colors">
                  <span>Lihat Analisis Spektrum</span>
                  <span>→</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}
