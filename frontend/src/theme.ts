/**
 * v1.9.3: 사이트 전역 테마 관리.
 *
 * - CSS 변수 (--ax-*) 동적 수정 → 모든 컴포넌트가 즉시 반영
 * - localStorage에 사용자 커스텀 테마 저장 → 새로고침 시 복원
 * - ComponentsGallery의 ThemeEditor에서 편집 → 전체 사이트 적용
 *
 * 작동 원리: tailwind.config.js의 colors.ax-* 는 `rgb(var(--ax-*) / <alpha-value>)`
 * 형태이므로, 이 파일이 document.documentElement에 변수만 세팅하면 끝.
 */

export type ColorKey =
  | 'ax-bg' | 'ax-shell' | 'ax-panel' | 'ax-inner' | 'ax-surface'
  | 'ax-subtle' | 'ax-emphasis'
  | 'ax-border'
  | 'ax-accent' | 'ax-accent2'
  | 'ax-text' | 'ax-muted'
  | 'ax-success' | 'ax-warning' | 'ax-danger'
  | 'ax-blue' | 'ax-purple' | 'ax-green' | 'ax-amber' | 'ax-rose'

/** v1.9.4: typography + layout 토큰. 컬러와 같이 동적 수정 가능. */
export type MetricKey =
  | 'ax-base-size'    // body font-size (예: '14px')
  | 'ax-leading'      // line-height (예: '1.55')
  | 'ax-tracking'     // letter-spacing (예: '0em')
  | 'ax-radius'       // 카드/버튼 둥글기 (예: '0.75rem')
  | 'ax-card-pad'     // 카드 padding (예: '1.25rem')
  | 'ax-section-gap'  // 섹션 간 여백 (예: '2rem')

export type ThemeKey = ColorKey | MetricKey

export type ThemeValues = Record<ThemeKey, string>

/** v1.9.10 default — 회색 배경 + 흰색 카드 위계 (dribbble dashboard 톤)
 *  bg(회색) → panel(흰색) → subtle(연한 회색) 3단계 위계로 카드가 떠보이게.
 */
export const DEFAULT_THEME: ThemeValues = {
  // v1.9.57: darkness 비율 9/6.5/4/2/1 (균등 분포 X, 빨리 밝아짐)
  'ax-bg':       '#E8EBF0',  // depth 0 (darkness 9 — 페이지, 살짝만)
  'ax-shell':    '#F2F4F7',  // depth 1 (darkness 6.5 — 큰 점프)
  'ax-panel':    '#F7F9FB',  // depth 2 (darkness 4 — 또 점프)
  'ax-inner':    '#FBFCFD',  // depth 3 (darkness 2 — 거의 흰색)
  'ax-surface':  '#FFFFFF',  // depth 4 (darkness 1 — 흰색)
  'ax-subtle':   '#F0F2F6',  // hover
  'ax-emphasis': '#E0E4EB',  // 강조 marker (다시 어둡게)
  'ax-border':  '#E5E7E9',  // dribbble border
  'ax-accent':  '#3944E8',  // Follow 버튼
  'ax-accent2': '#8660E2',  // 차트 보라
  'ax-text':    '#171717',
  'ax-muted':   '#737373',
  'ax-success': '#1FBC8B',  // vivid emerald (차트와 어울림)
  'ax-warning': '#F9B854',  // 차트 노랑
  'ax-danger':  '#E35B57',  // 차트 빨강
  'ax-blue':    '#EFF6FF',
  'ax-purple':  '#F5F3FF',
  'ax-green':   '#ECFDF5',
  'ax-amber':   '#FFFBEB',
  'ax-rose':    '#FFF1F2',
  // typography & layout
  'ax-base-size':    '14px',
  'ax-leading':      '1.55',
  'ax-tracking':     '0em',
  'ax-radius':       '0.875rem',  // v1.9.26: 14px
  'ax-card-pad':     '1.375rem',  // v1.9.26: 22px
  'ax-section-gap':  '2rem',
}

// v1.9.57: 키 v6 — darkness 비율 9/6.5/4/2/1 적용
const LS_KEY = 'ax_theme_v6'
const OLD_LS_KEYS = ['ax_theme_v1', 'ax_theme_v2', 'ax_theme_v3', 'ax_theme_v4', 'ax_theme_v5']

function hexToRgb(hex: string): { r: number; g: number; b: number } | null {
  const m = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex.trim())
  if (!m) return null
  return { r: parseInt(m[1], 16), g: parseInt(m[2], 16), b: parseInt(m[3], 16) }
}

const METRIC_KEYS: ReadonlySet<string> = new Set<MetricKey>([
  'ax-base-size', 'ax-leading', 'ax-tracking', 'ax-radius', 'ax-card-pad', 'ax-section-gap',
])

export function applyTheme(values: Partial<ThemeValues>) {
  if (typeof document === 'undefined') return
  const root = document.documentElement
  Object.entries(values).forEach(([k, val]) => {
    if (!val) return
    // 색상: hex → RGB triple. metric: 값 그대로 (px, rem, em, 숫자 등).
    if (METRIC_KEYS.has(k)) {
      root.style.setProperty(`--${k}`, val)
    } else {
      const rgb = hexToRgb(val)
      if (rgb) root.style.setProperty(`--${k}`, `${rgb.r} ${rgb.g} ${rgb.b}`)
    }
  })
}

export function loadTheme(): ThemeValues {
  try {
    // v1.9.51: 옛 키들 자동 cleanup — 캐시된 옛 색이 새 default를 가리던 회귀 수정
    OLD_LS_KEYS.forEach(k => {
      try { localStorage.removeItem(k) } catch {}
    })
    const raw = localStorage.getItem(LS_KEY)
    if (!raw) return { ...DEFAULT_THEME }
    const saved = JSON.parse(raw) as Partial<ThemeValues>
    return { ...DEFAULT_THEME, ...saved }
  } catch {
    return { ...DEFAULT_THEME }
  }
}

export function saveTheme(values: ThemeValues) {
  try {
    localStorage.setItem(LS_KEY, JSON.stringify(values))
  } catch {}
}

export function resetTheme(): ThemeValues {
  try { localStorage.removeItem(LS_KEY) } catch {}
  applyTheme(DEFAULT_THEME)
  return { ...DEFAULT_THEME }
}

/** App mount 시 호출 — 저장된 테마 복원 */
export function bootstrapTheme(): ThemeValues {
  const theme = loadTheme()
  applyTheme(theme)
  return theme
}

/** 토큰의 사용 의도 라벨 — UI 표시용 */
export const TOKEN_INFO: Record<ThemeKey, { label: string; desc: string; group: string; control?: 'color' | 'slider'; min?: number; max?: number; step?: number; unit?: string }> = {
  // 색상
  'ax-bg':       { label: 'Background', desc: 'depth 0 — 페이지 전체 배경 (가장 진한 회색)', group: 'surface', control: 'color' },
  'ax-shell':    { label: 'Shell',      desc: 'depth 1 — 사이드바·헤더·main wrapper (페이지 위 떠있는 외층)', group: 'surface', control: 'color' },
  'ax-panel':    { label: 'Panel',      desc: 'depth 2 — Card 외층 (main 안의 큰 박스)', group: 'surface', control: 'color' },
  'ax-inner':    { label: 'Inner',      desc: 'depth 3 — Card 안 inner box (list 컨테이너 등)', group: 'surface', control: 'color' },
  'ax-surface':  { label: 'Surface',    desc: 'depth 4 — 가장 안쪽 / 모달 (흰색)', group: 'surface', control: 'color' },
  'ax-subtle':   { label: 'Subtle',     desc: 'hover (shell과 panel 사이)', group: 'surface', control: 'color' },
  'ax-emphasis': { label: 'Emphasis',   desc: '강조 marker (큰 숫자 박스 등, 어두운 회색)', group: 'surface', control: 'color' },
  'ax-border':  { label: 'Border',     desc: '카드/구분선 테두리', group: 'surface', control: 'color' },

  'ax-accent':  { label: 'Accent',     desc: '주 액션, 링크, 활성 강조', group: 'brand', control: 'color' },
  'ax-accent2': { label: 'Accent 2',   desc: 'gradient 보조 컬러', group: 'brand', control: 'color' },

  'ax-text':    { label: 'Text',       desc: '본문 텍스트', group: 'type', control: 'color' },
  'ax-muted':   { label: 'Muted',      desc: '보조 텍스트, 캡션', group: 'type', control: 'color' },

  'ax-success': { label: 'Success',    desc: '정상, 통과 신호', group: 'semantic', control: 'color' },
  'ax-warning': { label: 'Warning',    desc: '경고, 주의', group: 'semantic', control: 'color' },
  'ax-danger':  { label: 'Danger',     desc: '에러, 위험, 삭제', group: 'semantic', control: 'color' },

  'ax-blue':    { label: 'Pastel Blue',   desc: 'Card variant', group: 'pastel', control: 'color' },
  'ax-purple':  { label: 'Pastel Purple', desc: 'Card variant', group: 'pastel', control: 'color' },
  'ax-green':   { label: 'Pastel Green',  desc: 'Card variant', group: 'pastel', control: 'color' },
  'ax-amber':   { label: 'Pastel Amber',  desc: 'Card variant', group: 'pastel', control: 'color' },
  'ax-rose':    { label: 'Pastel Rose',   desc: 'Card variant', group: 'pastel', control: 'color' },

  // typography metrics (v1.9.4 신규)
  'ax-base-size':   { label: 'Font size',      desc: 'body 기본 font-size (전체 폰트 크기 스케일 영향)', group: 'metrics', control: 'slider', min: 12, max: 18, step: 0.5, unit: 'px' },
  'ax-leading':     { label: 'Line height',    desc: 'body 줄 간격 (행간)', group: 'metrics', control: 'slider', min: 1.2, max: 2.0, step: 0.05, unit: '' },
  'ax-tracking':    { label: 'Letter spacing', desc: 'body 글자 간격 (자간, em 단위)', group: 'metrics', control: 'slider', min: -0.05, max: 0.1, step: 0.005, unit: 'em' },
  'ax-radius':      { label: 'Radius',         desc: '카드/버튼 둥글기', group: 'metrics', control: 'slider', min: 0, max: 1.5, step: 0.05, unit: 'rem' },
  'ax-card-pad':    { label: 'Card padding',   desc: '카드 내부 여백', group: 'metrics', control: 'slider', min: 0.5, max: 2.5, step: 0.1, unit: 'rem' },
  'ax-section-gap': { label: 'Section gap',    desc: '섹션 간 여백', group: 'metrics', control: 'slider', min: 1, max: 4, step: 0.25, unit: 'rem' },
}
