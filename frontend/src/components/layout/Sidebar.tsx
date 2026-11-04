import { X } from 'lucide-react';
import { NavLink } from 'react-router-dom';
import { NAV_ITEMS } from '../../config/navigation';
import type { HealthCheckResult } from '../../types/health';
import { BackendStatus } from '../common/BackendStatus';
import { Logo } from '../common/Logo';

interface SidebarProps {
  health: HealthCheckResult;
  /** Mobile drawer state. Ignored on large screens, where the sidebar is always visible. */
  isOpen: boolean;
  onClose: () => void;
}

export function Sidebar({ health, isOpen, onClose }: SidebarProps) {
  return (
    <>
      {/* Backdrop for the mobile drawer */}
      <div
        aria-hidden="true"
        onClick={onClose}
        className={`fixed inset-0 z-40 bg-black/40 transition-opacity lg:hidden ${
          isOpen ? 'opacity-100' : 'pointer-events-none opacity-0'
        }`}
      />

      <aside
        aria-label="Primary"
        className={`fixed inset-y-0 left-0 z-50 flex w-72 flex-col border-r border-line bg-sidebar transition-transform duration-200 lg:sticky lg:top-0 lg:z-auto lg:h-screen lg:w-64 lg:shrink-0 lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        <div className="flex h-16 items-center justify-between px-6 pt-2">
          <Logo />
          <button
            type="button"
            onClick={onClose}
            aria-label="Close navigation"
            className="rounded-lg p-1.5 text-muted transition-colors hover:bg-surface-2 hover:text-ink lg:hidden"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        <nav className="mt-6 flex-1 space-y-1 px-3">
          {NAV_ITEMS.map(({ label, path, icon: Icon }) => (
            <NavLink
              key={path}
              to={path}
              end={path === '/'}
              onClick={onClose}
              className={({ isActive }) =>
                `relative flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-accent-soft text-accent-ink before:absolute before:-left-3 before:top-1/2 before:h-5 before:w-[3px] before:-translate-y-1/2 before:rounded-r-full before:bg-accent before:content-['']"
                    : 'text-muted hover:bg-surface-2 hover:text-ink'
                }`
              }
            >
              <Icon className="h-[18px] w-[18px] shrink-0" strokeWidth={1.9} />
              {label}
            </NavLink>
          ))}
        </nav>

        <div className="p-4">
          <BackendStatus health={health} />
        </div>
      </aside>
    </>
  );
}

