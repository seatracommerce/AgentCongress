import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
  safelist: [
    // Caucus colors — must be safelisted so Tailwind doesn't purge dynamic classes
    "bg-purple-100", "border-purple-400", "text-purple-800",
    "bg-blue-100", "border-blue-400", "text-blue-800",
    "bg-red-100", "border-red-400", "text-red-800",
    "bg-rose-100", "border-rose-500", "text-rose-900",
    "bg-green-100", "border-green-500", "text-green-800",
    "bg-amber-100", "border-amber-500", "text-amber-800",
    "bg-slate-100", "border-slate-500", "text-slate-800",
  ],
};
export default config;
