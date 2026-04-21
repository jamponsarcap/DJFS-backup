/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          900: '#050E1F',
          800: '#0A1628',
          700: '#0F2040',
          600: '#163055',
        },
        teal: {
          400: '#00D2FF',
          500: '#00BFFF',
          600: '#009FD4',
        },
      },
    },
  },
  plugins: [],
}
