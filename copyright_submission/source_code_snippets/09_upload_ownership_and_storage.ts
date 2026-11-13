0029    try {
0030      const formData = await request.formData()
0031      const formFile = formData.get('file')
0032      if (!(formFile instanceof File)) return NextResponse.json({ error: 'Resume file is required.' }, { status: 400 })
0033      file = formFile
0034    } catch {
0035      return NextResponse.json({ error: 'The upload request could not be read.' }, { status: 400 })
0036    }
0037
0038    if (!isSupportedResumeType(file.type)) return NextResponse.json({ error: 'Only PDF and DOCX resumes are supported.' }, { status: 400 })
0039    const validation = validateResumeFile(file)
0040    if (!validation.ok) return NextResponse.json({ error: validation.error }, { status: 400 })
0041
0042    const buffer = Buffer.from(await file.arrayBuffer())
0043    let extractedText: string
0044    try {
0045      extractedText = await extractResumeText(file.type, buffer)
0046    } catch (error) {
0047      console.error('Resume extraction failed', {
0048        filename: file.name,
0049        mimeType: file.type,
0050        size: file.size,
0051        error,
0052      })
0053      const message = error instanceof Error ? error.message : ''
0054      return NextResponse.json({
0055        error: message.includes('enough readable text')
0056          ? 'We could not find enough selectable text in that resume. Please upload a text-based PDF or DOCX file.'
0057          : 'We could not read that resume. Please check that the file is not corrupted or password-protected.',
0058      }, { status: 422 })
0059    }
0060
0061    const storagePath = `${auth.user.id}/${randomUUID()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`
0062    const workflowToken = randomUUID()
0063    const supabase = await createSupabaseServerClient()
0064    const storageResult = await supabase.storage.from('resumes').upload(storagePath, buffer, { contentType: file.type, upsert: false })
0065    if (storageResult.error) {
0066      console.error('Resume storage persistence failed', { filename: file.name, error: storageResult.error })
0067      return NextResponse.json({ error: 'The resume could not be stored securely. Please try again.' }, { status: 503 })
0068    }
0069
0070    try {
0071      const result = await pool.query(
0072        `INSERT INTO resumes (owner_id, filename, mime_type, size_bytes, extracted_text, storage_path, workflow_token) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id, filename, created_at, workflow_token`,
0073        [auth.user.id, file.name, file.type, file.size, extractedText.trim(), storagePath, workflowToken],
0074      )
0075
0076      return NextResponse.json({ resume: result.rows[0] }, { status: 201 })
0077    } catch (error) {
0078      await supabase.storage.from('resumes').remove([storagePath]).catch((cleanupError) => console.error('Resume storage cleanup failed', cleanupError))
0079      console.error('Resume persistence failed', { filename: file.name, error })
0080      return NextResponse.json({ error: 'The resume was extracted but could not be saved. Please try again.' }, { status: 503 })
