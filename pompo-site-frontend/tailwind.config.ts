import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0B0E2A",
        indigo: {
          DEFAULT: "#4338F5",
          50: "#EEEDFE",
          100: "#DCDAFD",
          400: "#6C63F7",
          500: "#4338F5",
          600: "#372DD6",
          700: "#2C24AC",
        },
        violet: {
          DEFAULT: "#9333EA",
          50: "#F5EBFD",
          100: "#E9D6FB",
          400: "#A855F0",
          500: "#9333EA",
          600: "#7A22C9",
        },
        teal: {
          DEFAULT: "#0EA5A5",
          400: "#22BFBF",
          500: "#0EA5A5",
        },
        mist: "#F5F5FB",
        slate: {
          soft: "#5B5F73",
          line: "#E4E4F0",
        },
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"],
        body: ["var(--font-body)", "sans-serif"],
      },
      maxWidth: {
        content: "1200px",
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #4338F5 0%, #9333EA 100%)",
        "brand-gradient-soft": "linear-gradient(135deg, #EEEDFE 0%, #F5EBFD 100%)",
      },
      keyframes: {
        "flow-dash": {
          to: { strokeDashoffset: "-200" },
        },
        "fade-up": {
          from: { opacity: "0", transform: "translateY(14px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
      },
      animation: {
        "flow-dash": "flow-dash 6s linear infinite",
        "fade-up": "fade-up 0.7s ease-out both",
      },
    },
  },
  plugins: [],
};

export default config;
