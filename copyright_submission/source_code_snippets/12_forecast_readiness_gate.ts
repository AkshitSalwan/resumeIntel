0001  import { readFile } from 'node:fs/promises'
0002  import path from 'node:path'
0003
0004  export type ForecastReadinessResponse = {
0005    error: 'forecast_unavailable'
0006    code: 'FORECAST_INSUFFICIENT_DATA'
0007    message: string
0008    readiness: Record<string, unknown> | null
0009  }
0010
0011  export async function forecastReadiness(): Promise<ForecastReadinessResponse> {
0012    const reportPath = path.join(process.cwd(), 'ml', 'skill-intelligence', 'data', 'job-postings', 'reports', 'forecasting', 'forecast_readiness.json')
0013    try {
0014      const report = JSON.parse(await readFile(reportPath, 'utf8')) as { readiness?: Record<string, unknown>; forecast_support?: Record<string, unknown> }
0015      return {
0016        error: 'forecast_unavailable',
0017        code: 'FORECAST_INSUFFICIENT_DATA',
0018        message: String(report.forecast_support?.reason ?? 'Reliable historical data is insufficient for validated forecasting.'),
0019        readiness: report.readiness ?? null,
0020      }
0021    } catch {
0022      return {
0023        error: 'forecast_unavailable',
0024        code: 'FORECAST_INSUFFICIENT_DATA',
0025        message: 'Reliable historical data is insufficient for validated forecasting.',
0026        readiness: null,
0027      }
0028    }
0029  }
