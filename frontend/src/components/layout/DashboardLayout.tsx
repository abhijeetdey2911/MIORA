import { useEffect, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { findNavItem } from '../../config/navigation';
import { SAMPLE_USER } from '../../data/dashboardSample';
import { useBackendHealth } from '../../hooks/useBackendHealth';
import { useNow } from '../../hooks/useNow';
import { useTheme } from '../../hooks/useTheme';
import { getGreeting } from '../../utils/date';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

export function DashboardLayout() {
  const { theme, toggleTheme } = useTheme();
  const health = useBackendHealth();
  const now = useNow();
  const { pathname } = useLocation();
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  useEffect(() => {
    if (!isMenuOpen) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setIsMenuOpen(false);
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [isMenuOpen]);

  const page = findNavItem(pathname);
  const isDashboard = pathname === '/';

  return (
    <div className="flex min-h-screen bg-app text-ink">
      <Sidebar health={health} isOpen={isMenuOpen} onClose={() => setIsMenuOpen(false)} />

      <div className="bg-grid min-w-0 flex-1">
        <div className="mx-auto w-full max-w-6xl px-4 py-6 sm:px-6 lg:px-8 lg:py-8">
          <Header
            eyebrow={isDashboard ? `${getGreeting(now)}, ${SAMPLE_USER.name} 👋` : undefined}
            title={page?.title ?? 'Page not found'}
            subtitle={page?.description ?? 'The page you are looking for does not exist.'}
            date={now}
            theme={theme}
            onToggleTheme={toggleTheme}
            onOpenMenu={() => setIsMenuOpen(true)}
          />

          <main className="mt-8">
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
