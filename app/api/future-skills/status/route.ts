import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'

export const runtime = 'nodejs'

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) {
    return NextResponse.json(
      { error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view Future Skills Intelligence.' },
      { status: auth.error === 'not_configured' ? 503 : 401 },
    )
  }
  const enabled = process.env.RESUMEINTEL_FUTURE_SKILLS_ENABLED === 'true'
  return NextResponse.json({
    enabled,
    status: enabled ? 'pending_validated_runtime' : 'disabled',
    message: enabled
      ? 'Future Skills Intelligence is enabled but requires a validated model runtime.'
      : 'Future Skills Intelligence is disabled until a validated adapter is deployed.',
    numerical_forecasting_unchanged: true,
  }, { status: enabled ? 503 : 200 })
}
