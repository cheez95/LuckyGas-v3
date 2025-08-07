/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    './pages/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
    './app/**/*.{ts,tsx}',
    './src/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: {
        "2xl": "1400px",
      },
    },
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "#FF6B35",
          50: "#FFF2ED",
          100: "#FFE5DB",
          200: "#FFCBB7",
          300: "#FFB193",
          400: "#FF8E5A",
          500: "#FF6B35",
          600: "#E54E18",
          700: "#B83E13",
          800: "#8A2F0F",
          900: "#5C1F0A",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "#004E89",
          50: "#E6F0F8",
          100: "#CCE1F1",
          200: "#99C3E3",
          300: "#66A5D5",
          400: "#3387C7",
          500: "#004E89",
          600: "#003E6E",
          700: "#002F52",
          800: "#001F37",
          900: "#00101B",
          foreground: "hsl(var(--secondary-foreground))",
        },
        success: {
          DEFAULT: "#22C55E",
          50: "#F0FDF4",
          500: "#22C55E",
          700: "#15803D",
        },
        warning: {
          DEFAULT: "#EAB308",
          50: "#FEFCE8",
          500: "#EAB308",
          700: "#A16207",
        },
        error: {
          DEFAULT: "#EF4444",
          50: "#FEF2F2",
          500: "#EF4444",
          700: "#B91C1C",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: 0 },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: 0 },
        },
        "fade-in": {
          from: { opacity: 0 },
          to: { opacity: 1 },
        },
        "slide-in": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
        "progress-bar": {
          from: { transform: "translateX(-100%)" },
          to: { transform: "translateX(0)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up": "accordion-up 0.2s ease-out",
        "fade-in": "fade-in 0.5s ease-in-out",
        "slide-in": "slide-in 0.3s ease-out",
        "progress-bar": "progress-bar 2s ease-in-out",
      },
      fontFamily: {
        sans: ["Noto Sans TC", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [require("tailwindcss-animate")],
}