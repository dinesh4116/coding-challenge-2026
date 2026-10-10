/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#F0F9FF',
          100: '#E0F2FE',
          200: '#BAE6FD',
          500: '#0284C7',
          600: '#0369A1',
          700: '#075985',
        },
        triage: {
          promote: '#059669',
          'promote-bg': 'rgba(5, 150, 105, 0.08)',
          block: '#E11D48',
          'block-bg': 'rgba(225, 29, 72, 0.08)',
          ignore: '#D97706',
          'ignore-bg': 'rgba(217, 119, 6, 0.08)'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace']
      }
    },
  },
  plugins: [],
}
