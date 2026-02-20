/**
 * Utility functions.
 */

/**
 * Add alpha channel to a hex color string.
 * Dynamic hex+alpha can't be done via Tailwind classes.
 *
 * @example withAlpha('#C8F547', 0.3) => '#C8F5474D'
 */
export function withAlpha(hex: string, alpha: number): string {
  const clamped = Math.max(0, Math.min(1, alpha));
  const alphaHex = Math.round(clamped * 255)
    .toString(16)
    .padStart(2, '0');
  return `${hex}${alphaHex}`;
}

/**
 * Format milliseconds to human-readable duration.
 */
export function formatDuration(ms: number): string {
  if (ms < 1) return '<1ms';
  if (ms < 1000) return `${Math.round(ms)}ms`;
  if (ms < 60_000) return `${(ms / 1000).toFixed(1)}s`;
  const minutes = Math.floor(ms / 60_000);
  const seconds = ((ms % 60_000) / 1000).toFixed(0);
  return `${minutes}m ${seconds}s`;
}

/**
 * Format file size to human-readable string.
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  const size = bytes / Math.pow(1024, i);
  return `${size.toFixed(i > 0 ? 1 : 0)} ${units[i]}`;
}

/**
 * Convert accuracy string to numeric value (0-5 scale).
 */
export function accuracyToValue(accuracy: string): number {
  switch (accuracy) {
    case 'Very High': return 5;
    case 'High': return 4;
    case 'Medium': return 3;
    case 'Low': return 2;
    default: return 1;
  }
}

/**
 * Convert latency string to numeric value (0-5 scale, higher = faster).
 */
export function latencyToValue(latency: string): number {
  switch (latency) {
    case 'Low': return 5;
    case 'Low-Medium': return 4;
    case 'Medium': return 3;
    case 'Medium-High': return 2;
    case 'High': return 1;
    default: return 3;
  }
}

/**
 * Generate a unique ID for chat messages.
 */
export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

/**
 * Clamp a number between min and max.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

/**
 * Truncate text to maxLength with ellipsis.
 */
export function truncate(text: string, maxLength: number): string {
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength - 1) + '\u2026';
}

/**
 * Debounce a function call.
 */
export function debounce<T extends (...args: unknown[]) => void>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Parse SSE line from buffer.
 * Returns parsed event or null if line is incomplete.
 */
export function parseSSELine(line: string): { event: string; data: unknown } | null {
  if (!line.startsWith('data: ')) return null;
  try {
    const raw = line.slice(6);
    const parsed = JSON.parse(raw);
    return { event: parsed.event ?? 'message', data: parsed.data ?? parsed };
  } catch {
    return null;
  }
}
