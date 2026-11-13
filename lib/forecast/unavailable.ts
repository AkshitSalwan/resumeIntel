import type { ForecastUnavailableResponse } from './types'

export const FORECAST_UNAVAILABLE_STATUS = 503

export function forecastUnavailable(): ForecastUnavailableResponse {
  return {
    error: 'forecast_unavailable',
    message: 'The forecasting engine has not been integrated yet. No forecast data is available.',
    code: 'FORECAST_ENGINE_NOT_INTEGRATED',
  }
}
