import { describe, expect, it } from 'vitest'
import { forecastUnavailable } from '../lib/forecast/unavailable'
import { parseForecastQuery, isValidSkillId } from '../lib/forecast/validation'

describe('forecast contracts', () => {
  it('parses supported forecast filters and pagination', () => {
    const result = parseForecastQuery(new URLSearchParams('role=Data%20Engineer&horizon=5&page=2&limit=10'))
    expect(result).toEqual({
      role: 'Data Engineer',
      industry: null,
      region: null,
      horizon: 5,
      category: null,
      search: null,
      page: 2,
      limit: 10,
    })
  })

  it('rejects unsupported horizons and invalid pagination', () => {
    expect(parseForecastQuery(new URLSearchParams('horizon=2'))).toEqual({ error: 'horizon must be one of 1, 3, or 5.' })
    expect(parseForecastQuery(new URLSearchParams('limit=101'))).toEqual({ error: 'page must be positive and limit must be between 1 and 100.' })
  })

  it('validates skill ids without accepting path traversal', () => {
    expect(isValidSkillId('generative-ai')).toBe(true)
    expect(isValidSkillId('../private')).toBe(false)
    expect(isValidSkillId('skill/one')).toBe(false)
  })

  it('returns an explicit unavailable response without fabricated data', () => {
    expect(forecastUnavailable()).toEqual({
      error: 'forecast_unavailable',
      message: 'The forecasting engine has not been integrated yet. No forecast data is available.',
      code: 'FORECAST_ENGINE_NOT_INTEGRATED',
    })
  })
})
