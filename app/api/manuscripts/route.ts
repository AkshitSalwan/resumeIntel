import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { pool } from '@/lib/db'

export const runtime = 'nodejs'

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to view manuscripts.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  try {
    const [sections, revisions] = await Promise.all([
      pool.query('SELECT id, title, content, position, created_at, updated_at FROM manuscript_sections WHERE owner_id = $1 ORDER BY position ASC, created_at ASC', [auth.user.id]),
      pool.query('SELECT id, section_id, content, created_at FROM manuscript_revisions WHERE owner_id = $1 ORDER BY created_at ASC', [auth.user.id]),
    ])
    return NextResponse.json({ sections: sections.rows, revisions: revisions.rows })
  } catch (error) {
    console.error('Manuscript retrieval failed', error)
    return NextResponse.json({ error: 'Saved manuscripts could not be loaded.' }, { status: 503 })
  }
}

export async function POST(request: Request) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to save a manuscript.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const body = await request.json().catch(() => null)
  const content = typeof body?.content === 'string' ? body.content.trim() : ''
  const title = typeof body?.title === 'string' ? body.title.trim() : 'Untitled section'
  const sectionId = typeof body?.sectionId === 'string' ? body.sectionId.trim() : ''
  if (!content || content.length > 100_000) return NextResponse.json({ error: 'Manuscript content must contain 1 to 100,000 characters.' }, { status: 400 })
  if (title.length > 255) return NextResponse.json({ error: 'Section title must be 255 characters or fewer.' }, { status: 400 })
  const client = await pool.connect()
  try {
    await client.query('BEGIN')
    let section
    if (sectionId) {
      section = await client.query(
        'UPDATE manuscript_sections SET content = $1, updated_at = now() WHERE id = $2 AND owner_id = $3 RETURNING id, title, content, position, created_at, updated_at',
        [content, sectionId, auth.user.id],
      )
      if (!section.rows[0]) {
        await client.query('ROLLBACK')
        return NextResponse.json({ error: 'Manuscript section not found.' }, { status: 404 })
      }
    } else {
      section = await client.query(
        'INSERT INTO manuscript_sections (owner_id, title, content, position) VALUES ($1, $2, $3, COALESCE((SELECT max(position) + 1 FROM manuscript_sections WHERE owner_id = $1), 0)) RETURNING id, title, content, position, created_at, updated_at',
        [auth.user.id, title, content],
      )
    }
    const revision = await client.query(
      'INSERT INTO manuscript_revisions (owner_id, section_id, content) VALUES ($1, $2, $3) RETURNING id, section_id, content, created_at',
      [auth.user.id, section.rows[0].id, content],
    )
    await client.query('COMMIT')
    return NextResponse.json({ section: section.rows[0], revision: revision.rows[0] }, { status: 201 })
  } catch (error) {
    await client.query('ROLLBACK').catch((rollbackError) => console.error('Manuscript rollback failed', rollbackError))
    console.error('Manuscript save failed', error)
    return NextResponse.json({ error: 'The manuscript could not be saved.' }, { status: 503 })
  } finally {
    client.release()
  }
}
