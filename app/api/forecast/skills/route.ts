import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { forecastReadiness } from '@/lib/forecast/readiness'
import { parseForecastQuery } from '@/lib/forecast/validation'

export const runtime = 'nodejs'

export async function GET(request: Request) {
  const query = parseForecastQuery(new URL(request.url).searchParams)
  if ('error' in query) return NextResponse.json({ error: query.error }, { status: 400 })
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view forecasts.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  return NextResponse.json(await forecastReadiness(), { status: 503 })
}
