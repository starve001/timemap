/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{ts,tsx}',
    './components/**/*.{ts,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        ink: {
          900: '#1a1a1a',
          700: '#3d3d3d',
          500: '#6b6b6b',
          300: '#a8a8a8',
        },
        cinnabar: {
          DEFAULT: '#c43a31',
          light: '#e85d54',
        },
        gold: {
          DEFAULT: '#b8860b',
          light: '#d4a532',
        },
        jade: '#5b8c5a',
        silk: '#faf6f0',
        bamboo: '#ede4d3',
        paper: '#fefaf5',
      },
      fontFamily: {
        serif: ['Noto Serif SC', 'STSong', 'serif'],
        sans: ['Noto Sans SC', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
