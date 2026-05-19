export type Theme = 'dark' | 'light'

const KEY = 'teststand-theme'

export function getTheme(): Theme {
  return (localStorage.getItem(KEY) as Theme) ?? 'dark'
}

export function applyTheme(theme: Theme) {
  document.documentElement.classList.toggle('dark', theme === 'dark')
  localStorage.setItem(KEY, theme)
}

export function toggleTheme(): Theme {
  const next: Theme = getTheme() === 'dark' ? 'light' : 'dark'
  applyTheme(next)
  return next
}
