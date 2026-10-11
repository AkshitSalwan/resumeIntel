import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { getSupabaseConfig } from '../lib/supabase/config'

describe('security configuration', () => {
  it('does not expose privileged environment names to browser configuration', () => {
    expect(Object.keys(import.meta.env).filter((key) => key.startsWith('NEXT_PUBLIC_'))).not.toContain('NEXT_PUBLIC_SUPABASE_SECRET_KEY')
    const browserSource = readFileSync(resolve(process.cwd(), 'lib/supabase/browser.ts'), 'utf8')
    expect(browserSource).not.toContain('DATABASE_URL')
    expect(browserSource).not.toContain('SUPABASE_SECRET_KEY')
  })

  it('requires the public Supabase URL and publishable key', () => {
    const originalUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
    const originalKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
    delete process.env.NEXT_PUBLIC_SUPABASE_URL
    delete process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
    expect(() => getSupabaseConfig()).toThrow('Supabase authentication is not configured.')
    if (originalUrl) process.env.NEXT_PUBLIC_SUPABASE_URL = originalUrl
    if (originalKey) process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY = originalKey
  })

  it('defines RLS and private storage policies for every user-data table', () => {
    const schema = readFileSync(resolve(process.cwd(), 'supabase/schema.sql'), 'utf8')
    for (const table of ['resumes', 'analyses', 'research_experiments', 'research_runs', 'manuscript_sections', 'manuscript_revisions']) {
      expect(schema).toContain(`alter table ${table} enable row level security`)
    }
    expect(schema).toContain("values ('resumes', 'resumes', false)")
    expect(schema).toContain("storage.foldername(name))[1] = auth.uid()::text")
    expect(schema).toContain('exists (select 1 from resumes')
    expect(schema).toContain('exists (select 1 from manuscript_sections')
  })

  it('keeps protected resume and report routes behind session checks', () => {
    const resumeRoute = readFileSync(resolve(process.cwd(), 'app/api/resumes/route.ts'), 'utf8')
    const reportRoute = readFileSync(resolve(process.cwd(), 'app/api/analyses/[id]/route.ts'), 'utf8')

    expect(resumeRoute).toContain('const auth = await getAuthenticatedUser()')
    expect(resumeRoute).toContain("if (!auth.user)")
    expect(resumeRoute).toContain('auth.user.id')
    expect(reportRoute).toContain('const auth = await getAuthenticatedUser()')
    expect(reportRoute).toContain("if (!auth.user)")
  })

  it('keeps resume creation and report retrieval owner-scoped', () => {
    const resumeRoute = readFileSync(resolve(process.cwd(), 'app/api/resumes/route.ts'), 'utf8')
    const analysesRoute = readFileSync(resolve(process.cwd(), 'app/api/analyses/route.ts'), 'utf8')
    const reportRoute = readFileSync(resolve(process.cwd(), 'app/api/analyses/[id]/route.ts'), 'utf8')

    expect(resumeRoute).toContain('INSERT INTO resumes (owner_id')
    expect(resumeRoute).toContain('[auth.user.id, file.name')
    expect(analysesRoute).toContain('WHERE id = $1 AND owner_id = $2')
    expect(analysesRoute).toContain('[resumeId, auth.user.id]')
    expect(reportRoute).toContain('WHERE id = $1 AND owner_id = $2 LIMIT 1')
    expect(reportRoute).toContain('[id, auth.user.id]')
  })

  it('persists and retrieves the structured analysis result through the owner-scoped API', () => {
    const analysesRoute = readFileSync(resolve(process.cwd(), 'app/api/analyses/route.ts'), 'utf8')
    const reportRoute = readFileSync(resolve(process.cwd(), 'app/api/analyses/[id]/route.ts'), 'utf8')
    const schema = readFileSync(resolve(process.cwd(), 'supabase/schema.sql'), 'utf8')
    const analysisEngine = readFileSync(resolve(process.cwd(), 'lib/analysis.ts'), 'utf8')

    expect(schema).toContain('result jsonb not null')
    expect(analysesRoute).toContain('JSON.stringify(result)')
    expect(analysisEngine).toContain('proficiencies: estimateSkillProficiencies(resumeText)')
    expect(analysesRoute).toContain('RETURNING id, resume_id, job_description, result, created_at')
    expect(reportRoute).toContain('SELECT id, resume_id, job_description, result, created_at')
  })

  it('keeps auth UI on public Supabase configuration and protects the dashboard at the proxy', () => {
    const browserSource = readFileSync(resolve(process.cwd(), 'lib/supabase/browser.ts'), 'utf8')
    const authForm = readFileSync(resolve(process.cwd(), 'components/auth-form.tsx'), 'utf8')
    const proxy = readFileSync(resolve(process.cwd(), 'proxy.ts'), 'utf8')
    const signOut = readFileSync(resolve(process.cwd(), 'components/sign-out-button.tsx'), 'utf8')

    expect(browserSource).toContain('createBrowserClient')
    expect(authForm).toContain('createSupabaseBrowserClient')
    expect(authForm).not.toContain('SUPABASE_SECRET_KEY')
    expect(authForm).not.toContain('DATABASE_URL')
    expect(proxy).toContain("request.nextUrl.pathname === '/'")
    expect(proxy).toContain("url.pathname = '/auth/signin'")
    expect(signOut).toContain("fetch('/api/auth/signout'")
  })
})
