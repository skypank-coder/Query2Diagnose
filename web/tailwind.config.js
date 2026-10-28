/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        serif: ["'Source Serif 4'", "Georgia", "serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "monospace"],
      },
      colors: {
        accent: { 50: "#eef6f6", 100: "#d5eceb", 400: "#3fa29c", 500: "#2b8a84", 600: "#1f6f6a", 700: "#195956" },
      },
    },
  },
  plugins: [],
};
