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
        accent: { 50: "#eef6f6", 100: "#d5eceb", 200: "#a9d9d6", 300: "#72c0bb", 400: "#3fa29c", 500: "#2b8a84", 600: "#1f6f6a", 700: "#195956" },
      },
      keyframes: {
        "fade-up": { "0%": { opacity: "0", transform: "translateY(10px)" }, "100%": { opacity: "1", transform: "none" } },
      },
      animation: { "fade-up": "fade-up 0.6s ease-out both" },
    },
  },
  plugins: [],
};
