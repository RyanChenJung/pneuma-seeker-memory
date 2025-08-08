/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}", 
    "./components/**/*.{js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#7B1113', // UChicago Maroon
          50: '#F6E8E8',
          100: '#EBCBCB',
          200: '#D89A9A',
          300: '#C66969',
          400: '#B64646',
          500: '#7B1113',
          600: '#660E11',
          700: '#550C0E',
          800: '#440A0B',
          900: '#330708',
        }
      },
      fontFamily: {
        sans: ['-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'Oxygen',
               'Ubuntu', 'Cantarell', 'Fira Sans', 'Droid Sans', 'Helvetica Neue', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
