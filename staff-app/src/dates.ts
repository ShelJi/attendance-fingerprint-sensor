export const dateKey = (date: Date) => `${String(date.getFullYear()).padStart(4, '0')}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
export function clockTime(value: string | null) {
  if (!value) return '—';
  const match = /^(\d{2}):(\d{2})(?::\d{2})?$/.exec(value);
  if (match) return `${+match[1] % 12 || 12}:${match[2]} ${+match[1] < 12 ? 'AM' : 'PM'}`;
  return new Date(value).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true });
}
export function monthRange(date: Date) {
  const first = new Date(date); first.setDate(1);
  const last = new Date(first); last.setMonth(last.getMonth() + 1, 0);
  return { start_date: dateKey(first), end_date: dateKey(last) };
}
export function dateValid(value: string) { return /^\d{4}-\d{2}-\d{2}$/.test(value) && !Number.isNaN(Date.parse(value)) && new Date(value).toISOString().slice(0, 10) === value; }
export function validateRange(start: string, end: string) {
  if ((start && !dateValid(start)) || (end && !dateValid(end)) || (start && end && start > end)) throw new Error('Invalid dates.');
}
export function monthCells(year: number, month: number) {
  const first = new Date(0); first.setFullYear(year, month - 1, 1); first.setHours(12, 0, 0, 0);
  const count = new Date(first); count.setMonth(month); count.setDate(0);
  const days = count.getDate(); const offset = (first.getDay() + 6) % 7;
  return Array.from({ length: Math.ceil((offset + days) / 7) * 7 }, (_, index) => {
    const day = index - offset + 1;
    return day > 0 && day <= days ? `${String(year).padStart(4, '0')}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}` : null;
  });
}
export function shiftMonth(year: number, month: number, step: number) {
  const index = year * 12 + month - 1 + step;
  return { year: Math.floor(index / 12), month: index % 12 + 1 };
}
