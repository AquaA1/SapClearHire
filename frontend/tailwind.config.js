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

        /* ── Evidence domain (aligned to tokens) ──────── */
        evidence: {
          supported:    'var(--evidence-supported)',
          supportedBg:  'var(--evidence-supported-bg)',
          ambiguous:    'var(--evidence-ambiguous)',
          ambiguousBg:  'var(--evidence-ambiguous-bg)',
          notfound:     'var(--evidence-notfound)',
          notfoundBg:   'var(--evidence-notfound-bg)',
          verified:     'var(--evidence-verified)',
          clarified:    'var(--evidence-clarified)',
          clarifiedBg:  'var(--evidence-clarified-bg)',
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

      fontSize: {
        '2xs': ['0.75rem', { lineHeight: '1.1rem' }],
        xs:    ['0.84rem', { lineHeight: '1.25rem' }],
        sm:    ['0.94rem', { lineHeight: '1.4rem' }],
        base:  ['1.0625rem', { lineHeight: '1.65rem' }],
        lg:    ['1.2rem', { lineHeight: '1.75rem' }],
        xl:    ['1.35rem', { lineHeight: '1.875rem' }],
        '2xl': ['1.65rem', { lineHeight: '2.15rem' }],
        '3xl': ['2.1rem', { lineHeight: '2.5rem' }],
        '4xl': ['2.65rem', { lineHeight: '3rem' }],
      },

      borderRadius: {
        card:  'var(--radius-card)',  /* 22px */
        sm:    'var(--radius-sm)',    /* 10px */
        pill:  'var(--radius-pill)',  /* 9999px */
      },

      boxShadow: {
        card:       'var(--shadow-card)',
        'card-hover':'var(--shadow-card-hover)',
        dropdown:   'var(--shadow-dropdown)',
        modal:      'var(--shadow-modal)',
      },
    },
  },
  plugins: [],
}
