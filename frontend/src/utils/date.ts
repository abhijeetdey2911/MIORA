const DAY_MS = 24 * 60 * 60 * 1000;

export function getGreeting(date: Date = new Date()): string {
  const hour = date.getHours();
  if (hour < 12) return 'Good Morning';
  if (hour < 18) return 'Good Afternoon';
  return 'Good Evening';
}

/** e.g. "Mon, Nov 3, 2026" */
export function formatFullDate(date: Date = new Date()): string {
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

/** e.g. "Nov 3" */
export function formatShortDate(date: Date): string {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/** The last `count` days ending today, oldest first. */
export function getLastDays(count: number, today: Date = new Date()): Date[] {
  return Array.from({ length: count }, (_, index) => {
    const date = new Date(today.getTime() - (count - 1 - index) * DAY_MS);
    return date;
  });
}

/** e.g. 252 -> "4h 12m", 45 -> "45m" */
export function formatDuration(totalMinutes: number): string {
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  if (hours === 0) return `${minutes}m`;
  return `${hours}h ${minutes}m`;
}

