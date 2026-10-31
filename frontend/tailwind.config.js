/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        /* ── Token-backed semantic names ──────────────── */
        canvas:             'var(--canvas)',
        sidebar:            'var(--sidebar)',
        surface:            'var(--surface)',
        elevated:           'var(--elevated)',
        outer:              'var(--outer)',
        ink:                'var(--ink)',
        'ink-secondary':    'var(--ink-secondary)',
        muted:              'var(--muted)',
        'muted-dim':        'var(--muted-dim)',
        accent:             'var(--accent)',
        'accent-secondary': 'var(--accent-secondary)',
        'accent-dim':       'var(--accent-dim)',

        /* ── Restrained Coordinated Pastel Status ─────── */
        success:       'var(--success)',
        'success-dim': 'var(--success-dim)',
        info:          'var(--info)',
        'info-dim':    'var(--info-dim)',
        pending:       'var(--pending)',
        'pending-dim': 'var(--pending-dim)',
        warn:          'var(--warn)',
        'warn-dim':    'var(--warn-dim)',
        danger:        'var(--danger)',
        'danger-dim':  'var(--danger-dim)',

        /* ── Border ───────────────────────────────────── */
        subtle:          'var(--border)',
        'subtle-strong': 'var(--border-strong)',

        /* ── Evidence domain (aligned to pastel palette) ─ */
        evidence: {
          supported:    '#A5EDE3',
          supportedBg:  'rgba(165, 237, 227, 0.12)',
          ambiguous:    '#C5D9E8',
          ambiguousBg:  'rgba(197, 217, 232, 0.12)',
          notfound:     '#D6B9CF',
          notfoundBg:   'rgba(214, 185, 207, 0.12)',
          verified:     '#A5EDE3',
          clarified:    '#C8FFF5',
          clarifiedBg:  'rgba(200, 255, 245, 0.12)',
        },
      },

      borderColor: {
        subtle:        'var(--border)',
        'subtle-strong': 'var(--border-strong)',
      },

      fontFamily: {
        sans: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        manrope: ['Manrope', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['Manrope', 'monospace'],
      },

      borderRadius: {
        card:  'var(--radius-card)',  /* 22px */
        sm:    'var(--radius-sm)',    /* 10px */
        pill:  'var(--radius-pill)',  /* 9999px */
      },

      boxShadow: {
        card:       '0 1px 3px rgba(0,0,0,0.4), 0 4px 16px rgba(0,0,0,0.25)',
        'card-hover':'0 2px 6px rgba(0,0,0,0.5), 0 8px 24px rgba(0,0,0,0.35)',
        dropdown:   '0 8px 24px rgba(0,0,0,0.6)',
        modal:      '0 16px 48px rgba(0,0,0,0.8)',
      },
    },
  },
  plugins: [],
}
