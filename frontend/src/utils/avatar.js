const PALETTE = [
  '#4f46e5',
  '#16a34a',
  '#ea580c',
  '#9333ea',
  '#0891b2',
  '#dc2626',
  '#0d9488',
  '#d97706',
  '#2563eb',
  '#c026d3',
]

export function avatarColor(name) {
  if (!name || name.trim() === '' || name === 'Unknown') return '#94a3b8'
  let h = 0
  for (let i = 0; i < name.length; i++) {
    h = ((h << 5) - h) + name.charCodeAt(i)
    h |= 0
  }
  return PALETTE[Math.abs(h) % PALETTE.length]
}

export function initials(name) {
  if (!name || name.trim() === '' || name === 'Unknown') return '?'
  return name.trim().split(/\s+/).slice(0, 2).map(p => p[0]?.toUpperCase() || '').join('')
}
