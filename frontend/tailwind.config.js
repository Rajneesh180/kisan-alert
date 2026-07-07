/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
        display: ['"Plus Jakarta Sans"', "Inter", "sans-serif"],
      },
      colors: {
        // Tuned forest-green brand scale (not default Tailwind green).
        brand: {
          50: "#f2f8f4",
          100: "#e0efe4",
          200: "#c2dfca",
          300: "#94c6a3",
          400: "#5fa676",
          500: "#3c8a56",
          600: "#2c6f43",
          700: "#245838",
          800: "#20472e",
          900: "#1b3a27",
        },
        // Chart series (validated for CVD via the dataviz palette script).
        viz: { veg: "#2f855a", water: "#2563eb", et0: "#d97706" },
      },
      boxShadow: {
        card: "0 1px 2px rgba(16,24,20,0.04), 0 1px 3px rgba(16,24,20,0.05)",
        lift: "0 10px 30px -12px rgba(16,24,20,0.22)",
      },
      borderRadius: { "2xl": "1rem", "3xl": "1.5rem" },
    },
  },
  plugins: [],
};
