/** @type {import('tailwindcss').Config} */
export default { darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Studio dark — warm-tinted neutrals, not cold blue-black
        ink: {
          950: '#0c0b0f',
          900: '#111016',
          850: '#16151d',
          800: '#1c1b25',
          700: '#262533',
          600: '#2f2d40',
          500: '#3d3b52',
          400: '#5a5875',
          300: '#8987a3',
          100: '#e5e5e5',
          50:  '#fafafa',


        200: '#c5c3df',
        },
          // Dark neutrals for background layers
          dark: {
            900: '#111016',
            800: '#1c1b25',
            700: '#262533',
            600: '#2f2d40',
            500: '#3d3b52',
            400: '#5a5875',
            300: '#8987a3',
            200: '#c5c3df',
          },
        // Amber accent — confident, editorial, warm
        amber: {
          50:  '#fff8ed',
          100: '#ffefd0',
          200: '#ffd999',
          300: '#ffbf5e',
          400: '#ffa030',
          500: '#f97f0a',
          600: '#e06005',
          700: '#b94408',
          800: '#943410',
          900: '#792d11',
        },
        // Status colors
        jade:  { 400: '#34d399', 600: '#059669', 900: '#064e3b' },
        rose:  { 400: '#fb7185', 600: '#e11d48', 900: '#4c0519' },
        sun:   { 400: '#fbbf24', 600: '#d97706', 900: '#451a03' },
        sky:   { 400: '#38bdf8', 600: '#0284c7', 900: '#0c4a6e' },
      },
      fontFamily: {
        sans:    ['Inter', 'system-ui', 'sans-serif'],
        mono:    ['JetBrains Mono', 'monospace'],
        display: ['Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        '2xs': ['0.65rem', { lineHeight: '1rem' }],
      },
      letterSpacing: {
        tightest: '-0.04em',
        tighter:  '-0.02em',
      },
      borderRadius: {
        '2.5xl': '1.25rem',
      },
      animation: {
        'fade-up':      'fadeUp 0.35s cubic-bezier(0.16,1,0.3,1)',
        'fade-in':      'fadeIn 0.25s ease-out',
        'spin-slow':    'spin 2s linear infinite',
        'pulse-amber':  'pulseAmber 2s cubic-bezier(0.4,0,0.6,1) infinite',
        'progress':     'progressStripe 1.2s linear infinite',
        'shimmer':      'shimmer 1.5s infinite',
      },
      keyframes: {
        fadeUp:  { '0%': { opacity: '0', transform: 'translateY(10px)' }, '100%': { opacity: '1', transform: 'translateY(0)' } },
        fadeIn:  { '0%': { opacity: '0' }, '100%': { opacity: '1' } },
        pulseAmber: {
          '0%,100%': { boxShadow: '0 0 0 0 rgba(249,127,10,0.15)' },
          '50%':      { boxShadow: '0 0 0 6px rgba(249,127,10,0)' },
        },
        progressStripe: { '0%': { backgroundPosition: '0 0' }, '100%': { backgroundPosition: '40px 0' } },
        shimmer: { '0%': { backgroundPosition: '-400px 0' }, '100%': { backgroundPosition: '400px 0' } },
      },
      backgroundImage: {
        'amber-radial': 'radial-gradient(ellipse 600px 400px at 50% -100px, rgba(249,127,10,0.08) 0%, transparent 70%)',
        'stripe':       'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,0.04) 10px, rgba(255,255,255,0.04) 20px)',
      },
      boxShadow: {
        'card':    '0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.04)',
        'raised':  '0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(255,255,255,0.05)',
        'amber':   '0 0 0 1px rgba(249,127,10,0.5), 0 0 12px rgba(249,127,10,0.1)',
        'inset':   'inset 0 1px 0 rgba(255,255,255,0.06)',
      },
    },
  },
  plugins: [],
}
