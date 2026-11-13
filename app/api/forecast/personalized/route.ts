import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { forecastReadiness } from '@/lib/forecast/readiness'

export const runtime = 'nodejs'

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view your future skill gap.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  return NextResponse.json(await forecastReadiness(), { status: 503 })
}
