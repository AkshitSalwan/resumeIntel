export const FORECAST_HORIZONS = [1, 3, 5] as const
export type ForecastHorizon = (typeof FORECAST_HORIZONS)[number]

export type ForecastDataPoint = {
  period: string
  value: number
}

export type SkillForecast = {
  id: string
  skillId: string
  skillName: string
  category: string
  targetRole: string
  industry: string
  region: string
  currentDemand: number | null
  predictedDemand: number | null
  growthRate: number | null
  forecastHorizon: ForecastHorizon
  confidenceScore: number | null
  historicalData: ForecastDataPoint[]
  predictedData: ForecastDataPoint[]
  evidenceSources: string[]
  lastUpdated: string | null
}

export type ForecastOverview = {
  emergingSkillsCount: number | null
  highGrowthSkillsCount: number | null
  industryCoverage: number | null
  averageConfidence: number | null
  lastUpdated: string | null
}

export type PersonalizedSkillGap = {
  skillId: string
  skillName: string
  currentSkillStatus: 'missing' | 'developing' | 'proficient' | 'unknown'
  predictedImportance: 'low' | 'medium' | 'high' | 'unknown'
  priority: 'low' | 'medium' | 'high' | 'unknown'
  explanation: string | null
  recommendedLearningPath: string[] | null
}

export type ForecastQuery = {
  role: string | null
  industry: string | null
  region: string | null
  horizon: ForecastHorizon
  category: string | null
  search: string | null
  page: number
  limit: number
}

export type ForecastUnavailableResponse = {
  error: 'forecast_unavailable'
  message: string
  code: 'FORECAST_ENGINE_NOT_INTEGRATED'
}
