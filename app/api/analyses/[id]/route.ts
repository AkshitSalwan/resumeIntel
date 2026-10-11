import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { pool } from '@/lib/db'

export const runtime = 'nodejs'

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const { id } = await context.params
  if (!/^[0-9a-f-]{36}$/i.test(id)) return NextResponse.json({ error: 'Analysis not found.' }, { status: 404 })
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view this analysis.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  try {
    const result = await pool.query(
      `SELECT id, resume_id, job_description, result, created_at FROM analyses WHERE id = $1 AND owner_id = $2 LIMIT 1`,
      [id, auth.user.id],
    )
    if (!result.rows[0]) return NextResponse.json({ error: 'Analysis not found.' }, { status: 404 })
    return NextResponse.json({ analysis: result.rows[0] })
  } catch (error) {
    console.error('Analysis retrieval failed', { id, error })
    return NextResponse.json({ error: 'The saved analysis could not be loaded.' }, { status: 503 })
  }
}
