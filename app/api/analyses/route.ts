import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { analyzeResume, validateJobDescription } from '@/lib/analysis'
import { pool } from '@/lib/db'

export const runtime = 'nodejs'

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view analyses.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  try {
    const result = await pool.query(
      `SELECT id, resume_id, job_description, result, created_at FROM analyses WHERE owner_id = $1 ORDER BY created_at DESC LIMIT 20`,
      [auth.user.id],
    )
    return NextResponse.json({ analyses: result.rows })
  } catch (error) {
    console.error('Analysis history retrieval failed', error)
    return NextResponse.json({ error: 'Saved analyses could not be loaded.' }, { status: 503 })
  }
}

export async function POST(request: Request) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to create an analysis.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const body = await request.json().catch(() => null)
  const resumeId = typeof body?.resumeId === 'string' ? body.resumeId.trim() : ''
  const rawJobDescription = typeof body?.jobDescription === 'string' ? body.jobDescription : ''
  const validation = validateJobDescription(rawJobDescription)
  if (!resumeId || !validation.ok) return NextResponse.json({ error: !resumeId ? 'A resume is required.' : validation.error }, { status: 400 })

  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    const resume = await client.query(`SELECT id, extracted_text FROM resumes WHERE id = $1 AND owner_id = $2 LIMIT 1`, [resumeId, auth.user.id])
    if (!resume.rows[0]) {
      await client.query('ROLLBACK')
      return NextResponse.json({ error: 'Resume not found.' }, { status: 404 })
    }
    const result = analyzeResume(resume.rows[0].extracted_text, validation.value)
    const saved = await client.query(
      `INSERT INTO analyses (owner_id, resume_id, job_description, result) VALUES ($1, $2, $3, $4::jsonb) RETURNING id, resume_id, job_description, result, created_at`,
      [auth.user.id, resumeId, validation.value, JSON.stringify(result)],
    )
    await client.query('COMMIT')
    return NextResponse.json({ analysis: saved.rows[0] }, { status: 201 })
  } catch (error) {
    await client.query('ROLLBACK').catch((rollbackError) => console.error('Analysis rollback failed', rollbackError))
    console.error('Analysis persistence failed', { resumeId, error })
    return NextResponse.json({ error: 'The analysis could not be saved. Please try again.' }, { status: 503 })
  } finally {
    client.release()
  }
}
