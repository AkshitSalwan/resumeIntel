import { createClient } from '@supabase/supabase-js'
import { readFileSync, statSync } from 'node:fs'
import { randomUUID } from 'node:crypto'

const auditEnvPath = '.env.audit.local'

function loadAuditEnv(path) {
  let contents
  try {
    contents = readFileSync(path, 'utf8')
    const mode = statSync(path).mode & 0o777
    if ((mode & 0o077) !== 0) {
      throw new Error(`${path} must be readable only by its owner (chmod 600).`)
    }
  } catch (error) {
    console.error(error instanceof Error ? error.message : `Could not read ${path}.`)
    process.exitCode = 2
    return null
  }

  const values = {}
  for (const line of contents.split(/\r?\n/)) {
    const trimmed = line.trim()
    if (!trimmed || trimmed.startsWith('#')) continue
    const separator = trimmed.indexOf('=')
    if (separator <= 0) continue
    const name = trimmed.slice(0, separator).trim()
    const value = trimmed.slice(separator + 1).trim().replace(/^(['"])(.*)\1$/, '$2')
    values[name] = value
  }
  return values
}

const auditEnv = loadAuditEnv(auditEnvPath)
if (!auditEnv) process.exit(2)

const required = [
  'NEXT_PUBLIC_SUPABASE_URL',
  'NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY',
  'SUPABASE_TEST_USER_A_EMAIL',
  'SUPABASE_TEST_USER_A_PASSWORD',
  'SUPABASE_TEST_USER_B_EMAIL',
  'SUPABASE_TEST_USER_B_PASSWORD',
]

const missing = required.filter((name) => !auditEnv[name]?.trim())
if (missing.length > 0) {
  console.error(`Missing required integration-test variables: ${missing.join(', ')}`)
  console.error(`Configure ${auditEnvPath} with two dedicated non-production Supabase accounts. No test was run.`)
  process.exitCode = 2
} else {
  const url = auditEnv.NEXT_PUBLIC_SUPABASE_URL
  const key = auditEnv.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
  const productionUrl = (() => {
    try {
      const productionEnv = readFileSync('.env.local', 'utf8')
      return productionEnv.match(/^NEXT_PUBLIC_SUPABASE_URL=(.+)$/m)?.[1]?.trim()
    } catch {
      return undefined
    }
  })()
  if (!url || url === productionUrl) {
    console.error('The audit environment must target a separate non-production Supabase project. No test was run.')
    process.exit(2)
  }
  const clientFor = (email, password) => {
    const client = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } })
    return client.auth.signInWithPassword({ email, password }).then(({ data, error }) => {
      if (error || !data.user) throw new Error('A dedicated integration-test account could not sign in.')
      return client
    })
  }

  const failIfError = (label, result) => {
    if (result.error) throw new Error(`${label} failed: ${result.error.message}`)
    return result.data
  }
  const expectEmpty = (label, result) => {
    if (result.error) throw new Error(`${label} returned an error: ${result.error.message}`)
    if (result.data?.length) throw new Error(`${label} unexpectedly returned another user resource.`)
  }
  const expectDenied = (label, result) => {
    if (result.error || result.data == null || (Array.isArray(result.data) && result.data.length === 0)) return
    throw new Error(`${label} unexpectedly succeeded.`)
  }

  const created = {
    a: { resume: [], analysis: [], experiment: [], run: [], section: [], revision: [], profile: [], objects: [] },
    b: { resume: [], analysis: [], experiment: [], run: [], section: [], revision: [], profile: [], objects: [] },
    forged: [],
  }
  let a
  let b

  const cleanup = async (client, resources) => {
    for (const path of resources.objects) await client.storage.from('resumes').remove([path])
    const resourceKeys = {
      manuscript_revisions: 'revision',
      manuscript_sections: 'section',
      research_runs: 'run',
      research_experiments: 'experiment',
      analyses: 'analysis',
      resumes: 'resume',
      profiles: 'profile',
    }
    for (const [table, key] of Object.entries(resourceKeys)) {
      const ids = resources[key] ?? []
      for (const id of ids) await client.from(table).delete().eq('id', id)
    }
  }

  try {
    ;[a, b] = await Promise.all([
      clientFor(auditEnv.SUPABASE_TEST_USER_A_EMAIL, auditEnv.SUPABASE_TEST_USER_A_PASSWORD),
      clientFor(auditEnv.SUPABASE_TEST_USER_B_EMAIL, auditEnv.SUPABASE_TEST_USER_B_PASSWORD),
    ])
    const [{ data: aUser }, { data: bUser }] = await Promise.all([a.auth.getUser(), b.auth.getUser()])
    if (!aUser.user || !bUser.user || aUser.user.id === bUser.user.id) throw new Error('Integration accounts must be two distinct users.')

    const aId = aUser.user.id
    const bId = bUser.user.id
    const prefix = `rls-audit-${randomUUID()}`
    const aPath = `${aId}/${prefix}-a.txt`
    const bPath = `${bId}/${prefix}-b.txt`
    created.a.objects.push(aPath)
    created.b.objects.push(bPath)

    failIfError('User A storage upload', await a.storage.from('resumes').upload(aPath, new Blob(['A']), { contentType: 'text/plain' }))
    failIfError('User B storage upload', await b.storage.from('resumes').upload(bPath, new Blob(['B']), { contentType: 'text/plain' }))
    failIfError('User A storage read', await a.storage.from('resumes').download(aPath))
    expectDenied('User B cross-user storage read', await b.storage.from('resumes').download(aPath))
    expectDenied('User B cross-user storage overwrite', await b.storage.from('resumes').update(aPath, new Blob(['forged']), { contentType: 'text/plain' }))
    expectDenied('User B cross-user storage delete', await b.storage.from('resumes').remove([aPath]))
    const direct = await fetch(`${url}/storage/v1/object/public/resumes/${aPath}`)
    if (direct.ok) throw new Error('Resume storage is publicly readable.')
    failIfError('User A storage update', await a.storage.from('resumes').update(aPath, new Blob(['updated']), { contentType: 'text/plain' }))
    failIfError('User A storage delete', await a.storage.from('resumes').remove([aPath]))
    created.a.objects.length = 0

    const resumeA = failIfError('User A resume insert', await a.from('resumes').insert({
      owner_id: aId, filename: `${prefix}-a.txt`, mime_type: 'text/plain', size_bytes: 1, extracted_text: 'A', storage_path: aPath,
    }).select('id').single())
    const resumeB = failIfError('User B resume insert', await b.from('resumes').insert({
      owner_id: bId, filename: `${prefix}-b.txt`, mime_type: 'text/plain', size_bytes: 1, extracted_text: 'B', storage_path: bPath,
    }).select('id').single())
    created.a.resume.push(resumeA.id)
    created.b.resume.push(resumeB.id)
    failIfError('User A own resume read', await a.from('resumes').select('id').eq('id', resumeA.id).single())
    expectEmpty('User A cross-user resume read', await a.from('resumes').select('id').eq('id', resumeB.id))
    failIfError('User A own resume update', await a.from('resumes').update({ filename: `${prefix}-a-updated.txt` }).eq('id', resumeA.id).select('id').single())
    expectEmpty('User A cross-user resume update', await a.from('resumes').update({ filename: 'forged.txt' }).eq('id', resumeB.id).select('id'))
    expectEmpty('User A cross-user resume delete', await a.from('resumes').delete().eq('id', resumeB.id).select('id'))
    const forged = await a.from('resumes').insert({
      owner_id: bId, filename: `${prefix}-forged.txt`, mime_type: 'text/plain', size_bytes: 1, extracted_text: 'forged',
    }).select('id').single()
    expectDenied('User A forged owner insert', forged)
    if (forged.data?.id) created.forged.push(forged.data.id)

    const analysisA = failIfError('User A analysis insert', await a.from('analyses').insert({
      owner_id: aId, resume_id: resumeA.id, job_description: 'A', result: { owner: 'A' },
    }).select('id').single())
    const analysisB = failIfError('User B analysis insert', await b.from('analyses').insert({
      owner_id: bId, resume_id: resumeB.id, job_description: 'B', result: { owner: 'B' },
    }).select('id').single())
    created.a.analysis.push(analysisA.id)
    created.b.analysis.push(analysisB.id)
    expectEmpty('User A cross-user analysis read', await a.from('analyses').select('id').eq('id', analysisB.id))
    expectEmpty('User A cross-user analysis update', await a.from('analyses').update({ job_description: 'forged' }).eq('id', analysisB.id).select('id'))
    expectEmpty('User A cross-user analysis delete', await a.from('analyses').delete().eq('id', analysisB.id).select('id'))

    const experimentA = failIfError('User A research insert', await a.from('research_experiments').insert({ owner_id: aId, name: prefix, kind: 'baseline', config: {} }).select('id').single())
    const experimentB = failIfError('User B research insert', await b.from('research_experiments').insert({ owner_id: bId, name: prefix, kind: 'baseline', config: {} }).select('id').single())
    created.a.experiment.push(experimentA.id)
    created.b.experiment.push(experimentB.id)
    const runA = failIfError('User A research run insert', await a.from('research_runs').insert({ owner_id: aId, experiment_id: experimentA.id, status: 'executed', result: {} }).select('id').single())
    const runB = failIfError('User B research run insert', await b.from('research_runs').insert({ owner_id: bId, experiment_id: experimentB.id, status: 'executed', result: {} }).select('id').single())
    created.a.run.push(runA.id)
    created.b.run.push(runB.id)
    expectEmpty('User A cross-user research read', await a.from('research_runs').select('id').eq('id', runB.id))

    const sectionA = failIfError('User A manuscript insert', await a.from('manuscript_sections').insert({ owner_id: aId, title: prefix, content: '', position: 0 }).select('id').single())
    const sectionB = failIfError('User B manuscript insert', await b.from('manuscript_sections').insert({ owner_id: bId, title: prefix, content: '', position: 0 }).select('id').single())
    created.a.section.push(sectionA.id)
    created.b.section.push(sectionB.id)
    const revisionA = failIfError('User A revision insert', await a.from('manuscript_revisions').insert({ owner_id: aId, section_id: sectionA.id, content: 'A' }).select('id').single())
    created.a.revision.push(revisionA.id)
    expectDenied('User A forged manuscript revision', await a.from('manuscript_revisions').insert({ owner_id: aId, section_id: sectionB.id, content: 'forged' }).select('id').single())
    expectEmpty('User A cross-user manuscript read', await a.from('manuscript_sections').select('id').eq('id', sectionB.id))

    const profileA = await a.from('profiles').select('id').eq('id', aId).maybeSingle()
    const profileB = await b.from('profiles').select('id').eq('id', bId).maybeSingle()
    if (profileA.error || profileB.error) throw new Error('Profile RLS verification could not inspect the dedicated test accounts.')
    if (!profileA.data) {
      failIfError('User A profile insert', await a.from('profiles').insert({ id: aId, display_name: prefix }).select('id').single())
      created.a.profile.push(aId)
    }
    if (!profileB.data) {
      failIfError('User B profile insert', await b.from('profiles').insert({ id: bId, display_name: prefix }).select('id').single())
      created.b.profile.push(bId)
    }
    expectEmpty('User A cross-user profile read', await a.from('profiles').select('id').eq('id', bId))

    const anonymous = createClient(url, key, { auth: { persistSession: false, autoRefreshToken: false } })
    expectEmpty('Unauthenticated resume read', await anonymous.from('resumes').select('id').eq('id', resumeA.id))
    expectDenied('Unauthenticated storage upload', await anonymous.storage.from('resumes').upload(`${prefix}-anonymous.txt`, new Blob(['x'])))
    console.log('PASS: two-user RLS and private storage integration audit completed.')
  } catch (error) {
    console.error(error instanceof Error ? `Live Supabase security audit failed: ${error.message}` : 'Live Supabase security audit failed.')
    process.exitCode = 1
  } finally {
    if (a) await cleanup(a, created.a)
    if (b) await cleanup(b, created.b)
    if (a && created.forged.length) await a.from('resumes').delete().in('id', created.forged)
  }
}
