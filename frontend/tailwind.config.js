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
        canvas:    'var(--canvas)',
        surface:   'var(--surface)',
        elevated:  'var(--elevated)',
        ink:       'var(--ink)',
        muted:     'var(--muted)',
        accent:    'var(--accent)',
        'accent-dim': 'var(--accent-dim)',

        /* ── Status ───────────────────────────────────── */
        success:  'var(--success)',
        'success-dim': 'var(--success-dim)',
        warn:     'var(--warn)',
        'warn-dim': 'var(--warn-dim)',
        danger:   'var(--danger)',
        'danger-dim': 'var(--danger-dim)',

        /* ── Border ───────────────────────────────────── */
        subtle:      'var(--border)',
        'subtle-strong': 'var(--border-strong)',

        /* ── Evidence domain ─────────────────────────── */
        evidence: {
          supported:    '#34D399',
          supportedBg:  'rgba(52, 211, 153, 0.12)',
          ambiguous:    '#F5A524',
          ambiguousBg:  'rgba(245, 165, 36, 0.12)',
          notfound:     '#F87171',
          notfoundBg:   'rgba(248, 113, 113, 0.12)',
          verified:     '#34D399',
          clarified:    '#3ECFBF',
          clarifiedBg:  'rgba(62, 207, 191, 0.12)',
        },
      },

      borderColor: {
        subtle:        'var(--border)',
        'subtle-strong': 'var(--border-strong)',
      },

      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'Cascadia Code', 'monospace'],
      },

      borderRadius: {
        card:  'var(--radius-card)',  /* 20px */
        sm:    'var(--radius-sm)',    /* 10px */
        pill:  'var(--radius-pill)',  /* 9999px */
        /* keep tailwind defaults: rounded-full, rounded-xl, rounded-lg, etc. */
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
