import type { Metadata } from "next";
import "./globals.css";
import { Navbar } from "@/components/Navbar";
import { Footer } from "@/components/Footer";
import { ShaderBackground } from "@/components/ShaderBackground";
import { AuthProvider } from "@/context/AuthContext";

export const metadata: Metadata = {
  title: "Stitch MCP · Deep Research Agent",
  description: "Autonomous local deep research analyst powered by LangGraph, MCP and local LLMs.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-on-surface antialiased min-h-screen relative overflow-x-hidden flex flex-col justify-between">
        <AuthProvider>
          <ShaderBackground />
          <Navbar />
          <main className="w-full pt-16 flex-1 min-h-[calc(100vh-140px)]">
            {children}
          </main>
          <Footer />
        </AuthProvider>
      </body>
    </html>
  );
}
