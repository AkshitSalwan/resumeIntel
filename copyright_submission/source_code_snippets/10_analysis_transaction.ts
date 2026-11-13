0024  export async function POST(request: Request) {
0025    const auth = await getAuthenticatedUser()
0026    if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to create an analysis.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
0027    const body = await request.json().catch(() => null)
0028    const resumeId = typeof body?.resumeId === 'string' ? body.resumeId.trim() : ''
0029    const workflowToken = typeof body?.workflowToken === 'string' ? body.workflowToken.trim() : ''
0030    const rawJobDescription = typeof body?.jobDescription === 'string' ? body.jobDescription : ''
0031    const validation = validateJobDescription(rawJobDescription)
0032    if (!resumeId || !validation.ok) return NextResponse.json({ error: !resumeId ? 'A resume is required.' : validation.error }, { status: 400 })
0033
0034    const client = await pool.connect()
0035    try {
0036      await client.query('BEGIN')
0037      const resume = await client.query(`SELECT id, extracted_text FROM resumes WHERE id = $1 AND owner_id = $2 LIMIT 1`, [resumeId, auth.user.id])
0038      if (!resume.rows[0]) {
0039        await client.query('ROLLBACK')
0040        return NextResponse.json({ error: 'Resume not found.' }, { status: 404 })
0041      }
0042      let result
0043      try {
0044        result = analyzeResume(resume.rows[0].extracted_text, validation.value)
0045      } catch (error) {
0046        await client.query('ROLLBACK')
0047        await cleanupFailedWorkflowResume(auth.user.id, resumeId, workflowToken)
0048        throw error
0049      }
0050      const saved = await client.query(
0051        `INSERT INTO analyses (owner_id, resume_id, job_description, result) VALUES ($1, $2, $3, $4::jsonb) RETURNING id, resume_id, job_description, result, created_at`,
0052        [auth.user.id, resumeId, validation.value, JSON.stringify(result)],
0053      )
0054      await client.query('COMMIT')
0055      return NextResponse.json({ analysis: saved.rows[0] }, { status: 201 })
0056    } catch (error) {
0057      await client.query('ROLLBACK').catch((rollbackError) => console.error('Analysis rollback failed', rollbackError))
0058      await cleanupFailedWorkflowResume(auth.user.id, resumeId, workflowToken)
0059      console.error('Analysis persistence failed', { resumeId, error })
0060      return NextResponse.json({ error: 'The analysis could not be saved. Please try again.' }, { status: 503 })
0061    } finally {
0062      client.release()
0063    }
0064
0065    async function cleanupFailedWorkflowResume(ownerId: string, resumeId: string, workflowToken: string) {
0066      if (!workflowToken) return
0067      try {
0068        const cleanup = await pool.query(
0069          'DELETE FROM resumes WHERE id = $1 AND owner_id = $2 AND workflow_token = $3 RETURNING storage_path',
0070          [resumeId, ownerId, workflowToken],
0071        )
0072        const storagePath = cleanup.rows[0]?.storage_path
0073        if (storagePath) {
