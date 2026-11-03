import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { pool } from '@/lib/db'

export const runtime = 'nodejs'

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view your profile.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  try {
    const profile = await pool.query('SELECT display_name FROM profiles WHERE id = $1 LIMIT 1', [auth.user.id])
    return NextResponse.json({ user: { id: auth.user.id, email: auth.user.email ?? null, displayName: profile.rows[0]?.display_name ?? null } })
  } catch (error) {
    console.error('Profile retrieval failed', error)
    return NextResponse.json({ error: 'Your profile could not be loaded.' }, { status: 503 })
  }
}
