/** @type {import('tailwindcss').Config} */
//
// v1.9.3: 모든 색상이 CSS 변수 (RGB triple) 참조.
// → ThemeEditor에서 :root의 변수만 변경하면 전체 사이트에 즉시 반영.
// → /<alpha-value> 슬롯으로 bg-ax-accent/50 같은 알파 변형도 지원.
//
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        ax: {
          bg:       'rgb(var(--ax-bg) / <alpha-value>)',         // depth 0
          shell:    'rgb(var(--ax-shell) / <alpha-value>)',      // v1.9.56: depth 1 (사이드바/헤더/main wrapper)
          panel:    'rgb(var(--ax-panel) / <alpha-value>)',      // depth 2 카드
          inner:    'rgb(var(--ax-inner) / <alpha-value>)',      // depth 3 카드 안
          surface:  'rgb(var(--ax-surface) / <alpha-value>)',    // depth 4 가장 안 (흰색)
          subtle:   'rgb(var(--ax-subtle) / <alpha-value>)',     // hover
          emphasis: 'rgb(var(--ax-emphasis) / <alpha-value>)',   // 강조 marker (작은 박스)
          border:  'rgb(var(--ax-border) / <alpha-value>)',
          accent:  'rgb(var(--ax-accent) / <alpha-value>)',
          accent2: 'rgb(var(--ax-accent2) / <alpha-value>)',
          text:    'rgb(var(--ax-text) / <alpha-value>)',
          muted:   'rgb(var(--ax-muted) / <alpha-value>)',
          success: 'rgb(var(--ax-success) / <alpha-value>)',
          warning: 'rgb(var(--ax-warning) / <alpha-value>)',
          danger:  'rgb(var(--ax-danger) / <alpha-value>)',
          // Pastel surfaces
          blue:    'rgb(var(--ax-blue) / <alpha-value>)',
          purple:  'rgb(var(--ax-purple) / <alpha-value>)',
          green:   'rgb(var(--ax-green) / <alpha-value>)',
          amber:   'rgb(var(--ax-amber) / <alpha-value>)',
          rose:    'rgb(var(--ax-rose) / <alpha-value>)',
          // v1.9.29: Chart palette (dribbble stacked bar 톤)
          'chart-1': 'rgb(var(--ax-chart-1) / <alpha-value>)',
          'chart-2': 'rgb(var(--ax-chart-2) / <alpha-value>)',
          'chart-3': 'rgb(var(--ax-chart-3) / <alpha-value>)',
          'chart-4': 'rgb(var(--ax-chart-4) / <alpha-value>)',
          'chart-5': 'rgb(var(--ax-chart-5) / <alpha-value>)',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      boxShadow: {
        'card':      '0 1px 2px rgba(0,0,0,0.04), 0 1px 3px rgba(0,0,0,0.03)',
        'card-hover':'0 2px 4px rgba(0,0,0,0.06), 0 4px 12px rgba(0,0,0,0.04)',
        'btn':       '0 1px 2px rgba(0,0,0,0.05)',
      },
      backgroundImage: {
        'gradient-ax':      'linear-gradient(135deg, rgb(var(--ax-accent)) 0%, rgb(var(--ax-accent2)) 100%)',
        'gradient-sidebar': 'linear-gradient(180deg, rgb(var(--ax-bg)) 0%, rgb(var(--ax-surface)) 100%)',
      },
    },
  },
  plugins: [],
}
