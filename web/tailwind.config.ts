import type { Config } from "tailwindcss";
import tailwindcssAnimate from "tailwindcss-animate";

const config: Config = {
  darkMode: ["class"],
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // BIM dark palette
        canvas:   "hsl(230, 15%, 8%)",   // main 3D canvas background
        panel:    "hsl(225, 12%, 11%)",  // left/right panel background
        surface:  "hsl(225, 10%, 15%)",  // cards, inputs
        border:   "hsl(225, 10%, 22%)",  // subtle borders
        accent:   "hsl(262, 80%, 65%)",  // purple — primary actions
        success:  "hsl(142, 70%, 45%)",  // job complete
        warning:  "hsl(45,  95%, 55%)",  // job running
        danger:   "hsl(0,   75%, 55%)",  // job error
        muted:    "hsl(225, 10%, 45%)",  // secondary text
      },
      fontFamily: {
        sans: ["var(--font-geist-sans)", "system-ui"],
        mono: ["var(--font-geist-mono)", "monospace"],
      },
      animation: {
        "pulse-fast": "pulse 1s ease-in-out infinite",
        "fade-in":    "fadeIn 0.3s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%":   { opacity: "0", transform: "translateY(4px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
      },
    },
  },
  plugins: [tailwindcssAnimate],
};

export default config;
