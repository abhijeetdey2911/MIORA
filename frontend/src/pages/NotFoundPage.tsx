import { ArrowLeft, Compass } from 'lucide-react';
import { Link } from 'react-router-dom';

export function NotFoundPage() {
  return (
    <div className="flex flex-col items-center rounded-2xl border border-dashed border-line bg-surface px-6 py-16 text-center shadow-card">
      <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-surface-2 text-muted">
        <Compass className="h-6 w-6" strokeWidth={1.9} />
      </div>
      <h2 className="mt-4 text-base font-semibold text-ink">Nothing here</h2>
      <p className="mt-1 max-w-sm text-sm text-muted">
        We couldn't find the page you were looking for.
      </p>
      <Link
        to="/"
        className="mt-6 inline-flex items-center gap-2 rounded-xl bg-accent px-4 py-2 text-sm font-medium text-white transition hover:brightness-105"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to dashboard
      </Link>
    </div>
  );
}
