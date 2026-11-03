const DASHBOARD_DATE_LOCALE = 'en-GB'
const DASHBOARD_DATE_TIME_ZONE = 'UTC'

/**
 * Dashboard dates use UTC so the server and browser agree around local
 * midnight, and en-GB to keep the displayed day-month order explicit.
 */
export function formatDashboardDate(date: Date): string {
  return new Intl.DateTimeFormat(DASHBOARD_DATE_LOCALE, {
    dateStyle: 'full',
    timeZone: DASHBOARD_DATE_TIME_ZONE,
  }).format(date).toUpperCase()
}
