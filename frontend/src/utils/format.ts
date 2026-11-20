const currency = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  maximumFractionDigits: 0,
});
const integer = new Intl.NumberFormat('en-US');

export const formatCurrency = (n: number): string => currency.format(n);
export const formatInteger = (n: number): string => integer.format(n);
export const formatPercent = (n: number, digits = 1): string => `${n.toFixed(digits)}%`;

export function getGreeting(date: Date = new Date()): string {
  const h = date.getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export function formatLongDate(date: Date = new Date()): string {
  return date.toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}
