export type Theme = 'light' | 'dark';

export const THEME_STORAGE_KEY = 'jobhunter-theme';

function isTheme(value: unknown): value is Theme {
  return value === 'light' || value === 'dark';
}

/** Theme previously chosen by the user, if any. */
export function getStoredTheme(): Theme | null {
  try {
    const value = window.localStorage.getItem(THEME_STORAGE_KEY);
    return isTheme(value) ? value : null;
  } catch {
    // localStorage can be unavailable (privacy mode, blocked storage).
    return null;
  }
}

export function getSystemTheme(): Theme {
  return window.matchMedia?.('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/** Stored preference first, then the OS preference. */
export function getInitialTheme(): Theme {
  return getStoredTheme() ?? getSystemTheme();
}

export function storeTheme(theme: Theme): void {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, theme);
  } catch {
    // Persistence is best-effort; the theme still applies for this session.
  }
}

/** Applies the theme to <html>. Transitions are suppressed briefly so the swap is instant. */
export function applyTheme(theme: Theme): void {
  const root = document.documentElement;
  if (root.dataset.theme === theme) return;

  root.classList.add('theme-switching');
  root.classList.toggle('dark', theme === 'dark');
  root.dataset.theme = theme;

  requestAnimationFrame(() =>
    requestAnimationFrame(() => root.classList.remove('theme-switching')),
  );
}

