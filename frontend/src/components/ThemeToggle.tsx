import { useState } from 'react'
import { getTheme, toggleTheme, type Theme } from '../utils/theme'

export function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>(getTheme)

  function handleToggle() {
    setTheme(toggleTheme())
  }

  return (
    <button
      onClick={handleToggle}
      title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
      className="cursor-pointer flex items-center gap-1.5 text-sm px-3 py-1.5 rounded-full font-semibold border transition-colors
        bg-slate-200 text-slate-700 border-slate-300 hover:bg-slate-300
        dark:bg-yellow-400/10 dark:text-yellow-300 dark:border-yellow-400/30 dark:hover:bg-yellow-400/20"
    >
      {theme === 'dark' ? '☀ Light' : '☾ Dark'}
    </button>
  )
}
