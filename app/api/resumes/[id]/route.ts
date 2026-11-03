import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { createSupabaseServerClient } from '@/lib/supabase/server'
import { pool } from '@/lib/db'

export const runtime = 'nodejs'

async function ownedResume(id: string, ownerId: string) {
  if (!/^[0-9a-f-]{36}$/i.test(id)) return null
  const result = await pool.query(
    'SELECT id, filename, mime_type, size_bytes, extracted_text, storage_path, created_at FROM resumes WHERE id = $1 AND owner_id = $2 LIMIT 1',
    [id, ownerId],
  )
  return result.rows[0] ?? null
}

export async function GET(_request: Request, context: { params: Promise<{ id: string }> }) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view this resume.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const { id } = await context.params
  try {
    const resume = await ownedResume(id, auth.user.id)
    if (!resume) return NextResponse.json({ error: 'Resume not found.' }, { status: 404 })
    return NextResponse.json({ resume })
  } catch (error) {
    console.error('Resume retrieval failed', { id, error })
    return NextResponse.json({ error: 'The resume could not be loaded.' }, { status: 503 })
  }
}

export async function PATCH(request: Request, context: { params: Promise<{ id: string }> }) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to update this resume.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const { id } = await context.params
  const body = await request.json().catch(() => null)
  const filename = typeof body?.filename === 'string' ? body.filename.trim() : ''
  if (!filename || filename.length > 255) return NextResponse.json({ error: 'A filename of 1 to 255 characters is required.' }, { status: 400 })
  try {
    const result = await pool.query(
      'UPDATE resumes SET filename = $1 WHERE id = $2 AND owner_id = $3 RETURNING id, filename, mime_type, size_bytes, storage_path, created_at',
      [filename, id, auth.user.id],
    )
    if (!result.rows[0]) return NextResponse.json({ error: 'Resume not found.' }, { status: 404 })
    return NextResponse.json({ resume: result.rows[0] })
  } catch (error) {
    console.error('Resume update failed', { id, error })
    return NextResponse.json({ error: 'The resume could not be updated.' }, { status: 503 })
  }
}

export async function DELETE(_request: Request, context: { params: Promise<{ id: string }> }) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to delete this resume.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const { id } = await context.params
  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    const result = await client.query(
      'DELETE FROM resumes WHERE id = $1 AND owner_id = $2 RETURNING id, storage_path',
      [id, auth.user.id],
    )
    if (!result.rows[0]) {
      await client.query('ROLLBACK')
      return NextResponse.json({ error: 'Resume not found.' }, { status: 404 })
    }
    await client.query('COMMIT')
    const storagePath = result.rows[0].storage_path
    if (storagePath) {
      const supabase = await createSupabaseServerClient()
      const storageResult = await supabase.storage.from('resumes').remove([storagePath])
      if (storageResult.error) {
        console.error('Resume storage deletion failed after database deletion', { id, error: storageResult.error })
        return NextResponse.json({ error: 'The resume record was deleted, but its private file could not be removed.' }, { status: 503 })
      }
    }
    return NextResponse.json({ deleted: true })
  } catch (error) {
    await client.query('ROLLBACK').catch((rollbackError) => console.error('Resume deletion rollback failed', { id, error: rollbackError }))
    console.error('Resume deletion failed', { id, error })
    return NextResponse.json({ error: 'The resume could not be deleted.' }, { status: 503 })
  } finally {
    client.release()
  }
}
