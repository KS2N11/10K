/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#e7f3ff',
          100: '#d1e7ff',
          200: '#acd5ff',
          300: '#7bbeff',
          400: '#489cff',
          500: '#1f77b4',
          600: '#1660a0',
          700: '#0e4a7f',
          800: '#0a3558',
          900: '#062234',
        },
        pain: {
          50: '#fff9e6',
          100: '#fff3cd',
          200: '#ffe69c',
          300: '#ffd86b',
          400: '#ffcb3a',
          500: '#ff6b35',
          600: '#e65522',
          700: '#cc3f0f',
          800: '#992f0b',
          900: '#662007',
        },
        success: {
          50: '#d1f2eb',
          100: '#a3e5d7',
          200: '#76d8c3',
          300: '#48cbaf',
          400: '#28a745',
          500: '#229639',
          600: '#1c862d',
          700: '#167521',
          800: '#106515',
          900: '#0a5409',
        },
      },
    },
  },
  plugins: [],
}
