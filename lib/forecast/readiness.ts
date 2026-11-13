import { readFile } from 'node:fs/promises'
import path from 'node:path'

export type ForecastReadinessResponse = {
  error: 'forecast_unavailable'
  code: 'FORECAST_INSUFFICIENT_DATA'
  message: string
  readiness: Record<string, unknown> | null
}

export async function forecastReadiness(): Promise<ForecastReadinessResponse> {
  const reportPath = path.join(process.cwd(), 'ml', 'skill-intelligence', 'data', 'job-postings', 'reports', 'forecasting', 'forecast_readiness.json')
  try {
    const report = JSON.parse(await readFile(reportPath, 'utf8')) as { readiness?: Record<string, unknown>; forecast_support?: Record<string, unknown> }
    return {
      error: 'forecast_unavailable',
      code: 'FORECAST_INSUFFICIENT_DATA',
      message: String(report.forecast_support?.reason ?? 'Reliable historical data is insufficient for validated forecasting.'),
      readiness: report.readiness ?? null,
    }
  } catch {
    return {
      error: 'forecast_unavailable',
      code: 'FORECAST_INSUFFICIENT_DATA',
      message: 'Reliable historical data is insufficient for validated forecasting.',
      readiness: null,
    }
  }
}
