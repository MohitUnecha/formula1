/**
 * Utility functions
 */

export function formatLapTime(seconds: number): string {
  if (!seconds || seconds === 0) return '--';
  
  const minutes = Math.floor(seconds / 60);
  const secs = (seconds % 60).toFixed(3);
  
  return `${minutes}:${secs.padStart(6, '0')}`;
}

export function formatGap(gap: number): string {
  if (gap === 0) return 'Leader';
  return `+${gap.toFixed(3)}s`;
}

export function formatDate(dateString: string): string {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
}

export function formatProbability(prob: number): string {
  return `${(prob * 100).toFixed(1)}%`;
}

export function getPositionSuffix(position: number): string {
  if (position === 1) return 'st';
  if (position === 2) return 'nd';
  if (position === 3) return 'rd';
  return 'th';
}

export function getPositionColor(position: number): string {
  if (position === 1) return 'text-yellow-400';
  if (position === 2) return 'text-gray-300';
  if (position === 3) return 'text-orange-400';
  if (position <= 10) return 'text-green-400';
  return 'text-gray-400';
}

export function getTyreColor(compound: string): string {
  const colors: Record<string, string> = {
    'SOFT': '#FF0000',
    'MEDIUM': '#FFD700',
    'HARD': '#FFFFFF',
    'INTERMEDIATE': '#00FF00',
    'WET': '#0000FF',
  };
  return colors[compound?.toUpperCase()] || '#888888';
}

export function cn(...classes: (string | boolean | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

export interface EventLike {
  event_id: number;
  event_date: string;
  round?: number;
  event_name?: string;
}

export function getCurrentOrUpcomingEvent<T extends EventLike>(events?: T[] | null): T | null {
  if (!events?.length) return null;

  const sorted = [...events].sort(
    (a, b) => new Date(a.event_date).getTime() - new Date(b.event_date).getTime(),
  );

  const now = new Date();
  now.setHours(0, 0, 0, 0);

  const upcoming = sorted.find((event) => new Date(event.event_date).getTime() >= now.getTime());
  return upcoming || sorted[sorted.length - 1] || null;
}
