/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}", // Это критически важно!
  ],
  theme: {
    extend: {
      colors: {
        vikki: {
          accent: '#00d2ff',
          success: '#34d399',
        }
      },
    },
  },
  plugins: [],
}