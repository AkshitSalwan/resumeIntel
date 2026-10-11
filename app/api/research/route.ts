import { NextResponse } from 'next/server'
import { getAuthenticatedUser } from '@/lib/auth'
import { pool } from '@/lib/db'
import { runExperiment, type ExperimentConfig } from '@/lib/research'

export async function POST(request: Request) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to use research.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  try {
    const body = await request.json() as Partial<ExperimentConfig> & { sectionId?: string; content?: string }
    if (body.sectionId && typeof body.content === 'string') {
      const revision = await pool.query(
        'INSERT INTO manuscript_revisions (owner_id, section_id, content) VALUES ($1, $2, $3) RETURNING id, section_id, content, created_at',
        [auth.user.id, body.sectionId, body.content],
      )
      return NextResponse.json({ revision: revision.rows[0] }, { status: 201 })
    }
    if (!body.name || !body.kind || !body.resumeText || !body.jobDescription) return NextResponse.json({ error: 'name, kind, resumeText, and jobDescription are required' }, { status: 400 })
    const config: ExperimentConfig = {
      name: body.name,
      kind: body.kind,
      resumeText: body.resumeText,
      jobDescription: body.jobDescription,
      transformation: body.transformation,
      baseline: body.baseline,
    }
    const result = runExperiment(config)
    const experiment = await pool.query(
      'INSERT INTO research_experiments (owner_id, name, kind, config) VALUES ($1, $2, $3, $4) RETURNING id, name, kind, config, created_at',
      [auth.user.id, config.name, config.kind, config],
    )
    const savedRun = await pool.query(
      'INSERT INTO research_runs (owner_id, experiment_id, status, result) VALUES ($1, $2, $3, $4) RETURNING id, experiment_id, status, result, executed_at',
      [auth.user.id, experiment.rows[0].id, 'executed', result],
    )
    return NextResponse.json({ experiment: experiment.rows[0], run: savedRun.rows[0] }, { status: 201 })
  } catch (error) {
    return NextResponse.json({ error: error instanceof Error ? error.message : 'Research run failed' }, { status: 400 })
  }
}

export async function GET() {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to use research.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  const [runs, sections] = await Promise.all([
    pool.query('SELECT id, experiment_id, status, result, executed_at FROM research_runs WHERE owner_id = $1 ORDER BY executed_at DESC LIMIT 20', [auth.user.id]),
    pool.query('SELECT id, title, content, updated_at FROM manuscript_sections WHERE owner_id = $1 ORDER BY position ASC, created_at ASC', [auth.user.id]),
  ])
  return NextResponse.json({ runs: runs.rows, sections: sections.rows })
}
