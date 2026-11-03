import { afterEach, describe, expect, it, vi } from 'vitest'
import { formatDashboardDate } from '../lib/date-format'

describe('formatDashboardDate', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses a deterministic locale and UTC date boundary', () => {
    expect(formatDashboardDate(new Date('2026-11-03T00:30:00-08:00'))).toBe('TUESDAY, 3 NOVEMBER 2026')
    expect(formatDashboardDate(new Date('2026-11-03T00:30:00+14:00'))).toBe('MONDAY, 2 NOVEMBER 2026')
  })

  it('does not use the runtime locale default', () => {
    const formatter = vi.spyOn(Intl, 'DateTimeFormat')
    formatDashboardDate(new Date('2026-11-03T12:00:00Z'))

    expect(formatter).toHaveBeenCalledWith('en-GB', {
      dateStyle: 'full',
      timeZone: 'UTC',
    })
  })
})
