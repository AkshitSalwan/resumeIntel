import { NextResponse } from 'next/server'
import { randomUUID } from 'node:crypto'
import { getAuthenticatedUser } from '@/lib/auth'
import { createSupabaseServerClient } from '@/lib/supabase/server'
import { pool } from '@/lib/db'
import { extractResumeText, isSupportedResumeType, validateResumeFile } from '@/lib/resume-extraction'

export const runtime = 'nodejs'

export async function POST(request: Request) {
  const auth = await getAuthenticatedUser()
  if (!auth.user) return NextResponse.json({ error: auth.error === 'not_configured' ? 'Authentication is not configured.' : 'Sign in to upload a resume.' }, { status: auth.error === 'not_configured' ? 503 : 401 })
  let file: File
  try {
    const formData = await request.formData()
    const formFile = formData.get('file')
    if (!(formFile instanceof File)) return NextResponse.json({ error: 'Resume file is required.' }, { status: 400 })
    file = formFile
  } catch {
    return NextResponse.json({ error: 'The upload request could not be read.' }, { status: 400 })
  }

  if (!isSupportedResumeType(file.type)) return NextResponse.json({ error: 'Only PDF and DOCX resumes are supported.' }, { status: 400 })
  const validation = validateResumeFile(file)
  if (!validation.ok) return NextResponse.json({ error: validation.error }, { status: 400 })

  const buffer = Buffer.from(await file.arrayBuffer())
  let extractedText: string
  try {
    extractedText = await extractResumeText(file.type, buffer)
  } catch (error) {
    console.error('Resume extraction failed', {
      filename: file.name,
      mimeType: file.type,
      size: file.size,
      error,
    })
    const message = error instanceof Error ? error.message : ''
    return NextResponse.json({
      error: message.includes('enough readable text')
        ? 'We could not find enough selectable text in that resume. Please upload a text-based PDF or DOCX file.'
        : 'We could not read that resume. Please check that the file is not corrupted or password-protected.',
    }, { status: 422 })
  }

  const storagePath = `${auth.user.id}/${randomUUID()}-${file.name.replace(/[^a-zA-Z0-9._-]/g, '_')}`
  const supabase = await createSupabaseServerClient()
  const storageResult = await supabase.storage.from('resumes').upload(storagePath, buffer, { contentType: file.type, upsert: false })
  if (storageResult.error) {
    console.error('Resume storage persistence failed', { filename: file.name, error: storageResult.error })
    return NextResponse.json({ error: 'The resume could not be stored securely. Please try again.' }, { status: 503 })
  }

  try {
    const result = await pool.query(
      `INSERT INTO resumes (owner_id, filename, mime_type, size_bytes, extracted_text, storage_path) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id, filename, created_at`,
      [auth.user.id, file.name, file.type, file.size, extractedText.trim(), storagePath],
    )

    return NextResponse.json({ resume: result.rows[0] }, { status: 201 })
  } catch (error) {
    await supabase.storage.from('resumes').remove([storagePath]).catch((cleanupError) => console.error('Resume storage cleanup failed', cleanupError))
    console.error('Resume persistence failed', { filename: file.name, error })
    return NextResponse.json({ error: 'The resume was extracted but could not be saved. Please try again.' }, { status: 503 })
  }
}
