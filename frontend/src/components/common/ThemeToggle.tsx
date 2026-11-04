import { Moon, Sun } from 'lucide-react';
import type { Theme } from '../../services/themeService';

interface ThemeToggleProps {
  theme: Theme;
  onToggle: () => void;
}

const OPTIONS = [
  { value: 'light', label: 'Light theme', icon: Sun },
  { value: 'dark', label: 'Dark theme', icon: Moon },
] as const;

export function ThemeToggle({ theme, onToggle }: ThemeToggleProps) {
  return (
    <div
      role="group"
      aria-label="Colour theme"
      className="inline-flex items-center rounded-full border border-line bg-surface p-1 shadow-card"
    >
      {OPTIONS.map(({ value, label, icon: Icon }) => {
        const isActive = theme === value;
        return (
          <button
            key={value}
            type="button"
            aria-label={label}
            aria-pressed={isActive}
            title={label}
            onClick={isActive ? undefined : onToggle}
            className={`flex h-7 w-7 items-center justify-center rounded-full transition-colors ${
              isActive
                ? 'bg-accent-soft text-accent-ink'
                : 'text-subtle hover:text-ink'
            }`}
          >
            <Icon className="h-4 w-4" strokeWidth={2} />
          </button>
        );
      })}
    </div>
  );
}

