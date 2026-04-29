/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          900: '#0B1320',
          700: '#12304D',
          500: '#1F6FA8',
          300: '#5FB6E5',
        },
      },
    },
  },
  plugins: [],
};
