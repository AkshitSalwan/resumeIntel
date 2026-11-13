import { FORECAST_HORIZONS, type ForecastHorizon, type ForecastQuery } from './types'

const MAX_FILTER_LENGTH = 120

function readFilter(value: string | null): string | null | undefined {
  if (value === null || value === '') return null
  const trimmed = value.trim()
  return trimmed && trimmed.length <= MAX_FILTER_LENGTH ? trimmed : undefined
}

function readPositiveInteger(value: string | null, fallback: number, maximum: number): number | undefined {
  if (value === null || value === '') return fallback
  if (!/^\d+$/.test(value)) return undefined
  const parsed = Number(value)
  return parsed > 0 && parsed <= maximum ? parsed : undefined
}

export function parseForecastQuery(searchParams: URLSearchParams): ForecastQuery | { error: string } {
  const horizonValue = searchParams.get('horizon')
  const horizon = horizonValue === null || horizonValue === '' ? 3 : Number(horizonValue)
  if (!FORECAST_HORIZONS.includes(horizon as ForecastHorizon)) {
    return { error: 'horizon must be one of 1, 3, or 5.' }
  }

  const role = readFilter(searchParams.get('role'))
  const industry = readFilter(searchParams.get('industry'))
  const region = readFilter(searchParams.get('region'))
  const category = readFilter(searchParams.get('category'))
  const search = readFilter(searchParams.get('search'))
  if (role === undefined || industry === undefined || region === undefined || category === undefined || search === undefined) {
    return { error: `Filters must be ${MAX_FILTER_LENGTH} characters or fewer.` }
  }

  const page = readPositiveInteger(searchParams.get('page'), 1, 100000)
  const limit = readPositiveInteger(searchParams.get('limit'), 20, 100)
  if (page === undefined || limit === undefined) return { error: 'page must be positive and limit must be between 1 and 100.' }

  return { role, industry, region, horizon: horizon as ForecastHorizon, category, search, page, limit }
}

export function isValidSkillId(skillId: string): boolean {
  return /^[a-zA-Z0-9_-]{1,120}$/.test(skillId)
}
