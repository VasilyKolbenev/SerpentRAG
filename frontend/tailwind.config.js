/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        serpent: {
          bg: '#080808',
          surface: '#0b0b0b',
          'surface-hover': '#0e0e0e',
          'surface-active': '#0f0f0f',
          border: '#181818',
          'border-light': '#151515',
          'border-hover': '#252525',
          text: '#e8e8e8',
          'text-secondary': '#d0d0d0',
          'text-tertiary': '#b0b0b0',
          'text-muted': '#787878',
          'text-dim': '#555555',
          'text-dark': '#444444',
          'text-darker': '#3a3a3a',
        },
        strategy: {
          agentic: '#C8F547',
          graph: '#8B5CF6',
          hybrid: '#2DD4A8',
          naive: '#38BDF8',
        },
        accent: {
          pink: '#F472B6',
          orange: '#FB923C',
        },
      },
      fontFamily: {
        outfit: ['Outfit', 'sans-serif'],
        'dm-sans': ['DM Sans', '-apple-system', 'sans-serif'],
        'dm-mono': ['DM Mono', 'monospace'],
      },
      keyframes: {
        fadeSlideUp: {
          from: { opacity: '0', transform: 'translateY(14px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        serpentFloat: {
          '0%, 100%': { transform: 'translate(0, 0) scale(1)' },
          '33%': { transform: 'translate(25px, -25px) scale(1.03)' },
          '66%': { transform: 'translate(-20px, 15px) scale(0.97)' },
        },
        pulse: {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
      },
      animation: {
        'fade-slide-up': 'fadeSlideUp 0.5s ease-out forwards',
        'serpent-float': 'serpentFloat 20s ease-in-out infinite',
        'serpent-float-reverse': 'serpentFloat 25s ease-in-out infinite reverse',
        'serpent-float-delayed': 'serpentFloat 30s ease-in-out infinite 5s',
        pulse: 'pulse 2s infinite',
      },
    },
  },
  plugins: [],
};
