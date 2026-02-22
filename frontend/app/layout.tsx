import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AgentCongress",
  description: "AI-simulated congressional debates on active US legislation",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
          <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-3">
            <span className="text-2xl">🏛️</span>
            <a href="/" className="text-xl font-bold tracking-tight text-gray-900 hover:text-blue-700">
              AgentCongress
            </a>
            <span className="text-sm text-gray-500 ml-1">
              AI-simulated caucus debates on live legislation
            </span>
            <nav className="ml-auto flex items-center gap-4 text-sm">
              <a href="/" className="text-gray-600 hover:text-blue-700 font-medium">
                Debates
              </a>
              <a href="/stats" className="text-gray-600 hover:text-blue-700 font-medium">
                Stats
              </a>
            </nav>
          </div>
        </header>
        <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
        <footer className="border-t border-gray-200 mt-16 py-6 text-center text-sm text-gray-400">
          AgentCongress — debates are AI-simulated and do not represent real caucus positions.
        </footer>
      </body>
    </html>
  );
}
