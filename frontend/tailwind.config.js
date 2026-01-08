/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',  // Only enable dark mode with explicit 'dark' class, not system preference
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}
