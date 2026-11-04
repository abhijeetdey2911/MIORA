interface LogoProps {
  /** Hide the wordmark and show the mark only. */
  markOnly?: boolean;
}

export function Logo({ markOnly = false }: LogoProps) {
  return (
    <div className="flex items-center gap-2.5">
      <svg
        width="26"
        height="26"
        viewBox="0 0 24 24"
        fill="none"
        aria-hidden="true"
        className="shrink-0 text-accent"
      >
        <path
          d="M12 2.5 22 21.5h-5.2L12 12.2 7.2 21.5H2L12 2.5Z"
          fill="currentColor"
        />
        <rect x="9.2" y="16" width="5.6" height="2.6" rx="1.3" fill="var(--sidebar)" />
      </svg>
      {!markOnly && (
        <span className="text-[17px] font-semibold tracking-tight text-ink">JobHunter</span>
      )}
    </div>
  );
}

