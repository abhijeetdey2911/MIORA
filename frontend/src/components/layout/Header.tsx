import { Menu } from 'lucide-react';
import type { Theme } from '../../services/themeService';
import { formatFullDate } from '../../utils/date';
import { ThemeToggle } from '../common/ThemeToggle';

interface HeaderProps {
  /** Small line above the title, e.g. a greeting. */
  eyebrow?: string;
  title: string;
  subtitle: string;
  /** Date shown in the header. */
  date: Date;
  theme: Theme;
  onToggleTheme: () => void;
  onOpenMenu: () => void;
}

export function Header({
  eyebrow,
  title,
  subtitle,
  date,
  theme,
  onToggleTheme,
  onOpenMenu,
}: HeaderProps) {
  return (
    <header className="flex items-start justify-between gap-4">
      <div className="flex min-w-0 items-start gap-3">
        <button
          type="button"
          onClick={onOpenMenu}
          aria-label="Open navigation"
          className="mt-0.5 shrink-0 rounded-xl border border-line bg-surface p-2 text-muted shadow-card transition-colors hover:text-ink lg:hidden"
        >
          <Menu className="h-5 w-5" />
        </button>

        <div className="min-w-0">
          {eyebrow && <p className="text-sm text-muted">{eyebrow}</p>}
          <h1 className="text-2xl font-semibold tracking-tight text-ink sm:text-[28px]">
            {title}
          </h1>
          <p className="mt-1 text-sm text-muted">{subtitle}</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <time
          dateTime={date.toISOString()}
          className="hidden whitespace-nowrap rounded-full border border-line bg-surface px-4 py-2 text-xs font-medium text-ink shadow-card md:inline-block"
        >
          {formatFullDate(date)}
        </time>

        <ThemeToggle theme={theme} onToggle={onToggleTheme} />

        <div
          title="Profile"
          className="flex h-9 w-9 items-center justify-center rounded-full bg-zinc-500 text-sm font-medium text-white dark:bg-zinc-600"
        >
          A
        </div>
      </div>
    </header>
  );
}
