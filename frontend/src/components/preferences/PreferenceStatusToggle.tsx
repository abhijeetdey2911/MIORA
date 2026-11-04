interface PreferenceStatusToggleProps {
  id?: string;
  isActive: boolean;
  disabled?: boolean;
  showHelperText?: boolean;
  label?: string;
  onChange: (nextIsActive: boolean) => void;
}

export function PreferenceStatusToggle({
  id,
  isActive,
  disabled = false,
  showHelperText = true,
  label,
  onChange,
}: PreferenceStatusToggleProps) {
  return (
    <div className="flex flex-col gap-1">
      <div className="flex items-center gap-2.5">
        <button
          id={id}
          type="button"
          role="switch"
          aria-checked={isActive}
          aria-label={
            label ?? (isActive ? 'Preference is Active' : 'Preference is Paused')
          }
          disabled={disabled}
          onClick={() => onChange(!isActive)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer items-center rounded-full border transition-colors duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent disabled:cursor-not-allowed disabled:opacity-60 ${
            isActive
              ? 'border-accent bg-accent'
              : 'border-line bg-surface-2'
          }`}
        >
          <span
            aria-hidden="true"
            className={`pointer-events-none inline-block h-4 w-4 rounded-full bg-white shadow-sm transition-transform duration-200 ${
              isActive ? 'translate-x-5' : 'translate-x-0.5'
            }`}
          />
        </button>

        <span
          className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold ${
            isActive
              ? 'bg-emerald-500/10 text-emerald-600 dark:bg-emerald-400/15 dark:text-emerald-300'
              : 'bg-surface-2 text-muted'
          }`}
        >
          <span
            className={`h-1.5 w-1.5 rounded-full ${
              isActive ? 'bg-emerald-500' : 'bg-subtle'
            }`}
          />
          {isActive ? 'Active' : 'Paused'}
        </span>
      </div>

      {showHelperText && (
        <p className="text-[11px] leading-snug text-muted">
          Paused preferences are excluded from future job discovery runs.
        </p>
      )}
    </div>
  );
}

