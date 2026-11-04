import type { NavItem } from '../config/navigation';

interface PlaceholderPageProps {
  item: NavItem;
}

export function PlaceholderPage({ item }: PlaceholderPageProps) {
  const Icon = item.icon;

  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line bg-surface px-6 py-16 text-center shadow-card">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-accent-soft text-accent-ink">
        <Icon className="h-6 w-6" strokeWidth={1.9} />
      </div>
      <h2 className="mt-4 text-base font-semibold text-ink">{item.label} is coming soon</h2>
      <p className="mt-1 max-w-sm text-sm text-muted">
        This section will be built in an upcoming phase.
      </p>
    </div>
  );
}

