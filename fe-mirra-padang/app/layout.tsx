import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import Navbar from "./components/Navbar";

// Menggunakan font Inter yang sangat bersih dan modern
const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "MIRRA | Structural Health Monitoring",
  description: "Model Integrated Real-time Representation Architecture. Sistem berbasis AIoT untuk pemantauan lingkungan dan kesehatan struktur jembatan secara real-time.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="id">
      <body className={`${inter.className} bg-[#FAFAFA] text-gray-900 antialiased`}>
        <Navbar />
        {children}
      </body>
    </html>
  );
}
