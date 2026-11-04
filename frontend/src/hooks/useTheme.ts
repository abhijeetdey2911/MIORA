import { useCallback, useEffect, useState } from 'react';
import {
  applyTheme,
  getInitialTheme,
  storeTheme,
  type Theme,
} from '../services/themeService';

export function useTheme() {
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    applyTheme(theme);
  }, [theme]);

  const toggleTheme = useCallback(() => {
    setTheme((current) => {
      const next: Theme = current === 'dark' ? 'light' : 'dark';
      storeTheme(next);
      return next;
    });
  }, []);

  return { theme, toggleTheme };
}

