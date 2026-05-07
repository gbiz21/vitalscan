/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0A0A0B",
          900: "#111113",
          850: "#17171A",
          800: "#1C1C20",
          700: "#27272D",
          600: "#3A3A42",
          500: "#5A5A63",
          400: "#8B8B95",
          300: "#B5B5BD",
          200: "#D8D8DD",
          100: "#EDEDF0",
          50: "#F8F8FA",
        },
        status: {
          normal: "#34D399",
          warning: "#FBBF24",
          danger: "#F87171",
        },
      },
      fontFamily: {
        sans: ['"Geist"', "system-ui", "sans-serif"],
        mono: ['"Geist Mono"', "ui-monospace", "monospace"],
      },
      animation: {
        "pulse-soft": "pulse-soft 1.4s ease-in-out infinite",
        "fade-in": "fade-in 0.4s ease-out",
        "scale-in": "scale-in 0.3s ease-out",
      },
      keyframes: {
        "pulse-soft": {
          "0%, 100%": { transform: "scale(1)", opacity: "1" },
          "50%": { transform: "scale(1.15)", opacity: "0.85" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        "scale-in": {
          from: { opacity: "0", transform: "scale(0.96)" },
          to: { opacity: "1", transform: "scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
