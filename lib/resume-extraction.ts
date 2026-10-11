import { normalizeText } from './analysis'

export const MAX_RESUME_BYTES = 10 * 1024 * 1024
export const SUPPORTED_RESUME_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
] as const

export type SupportedResumeType = (typeof SUPPORTED_RESUME_TYPES)[number]

export function validateResumeFile(file: Pick<File, 'name' | 'size' | 'type'>) {
  if (!SUPPORTED_RESUME_TYPES.includes(file.type as SupportedResumeType)) {
    return { ok: false as const, error: 'Only PDF and DOCX resumes are supported.' }
  }
  if (file.size === 0) return { ok: false as const, error: 'The resume file is empty.' }
  if (file.size > MAX_RESUME_BYTES) return { ok: false as const, error: 'Resume must be 10 MB or smaller.' }
  return { ok: true as const }
}

export function hasValidFileSignature(type: string, buffer: Buffer) {
  if (type === 'application/pdf') return buffer.subarray(0, 5).toString('ascii') === '%PDF-'
  if (type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
    return buffer.subarray(0, 2).toString('hex') === '504b'
  }
  return false
}

export function normalizeExtractedResumeText(text: string) {
  return normalizeText(text).replace(/\u0000/g, '')
}

export function assertReadableResumeText(text: string) {
  const normalized = normalizeExtractedResumeText(text)
  if (normalized.length < 40) throw new Error('The resume did not contain enough readable text.')
  return normalized
}

export async function extractResumeText(type: SupportedResumeType, buffer: Buffer) {
  if (!hasValidFileSignature(type, buffer)) throw new Error('The file signature does not match its declared type.')
  if (type === 'application/pdf') {
    const { getDocument } = await import('pdfjs-dist/legacy/build/pdf.mjs')
    const document = await getDocument({
      data: new Uint8Array(buffer),
      isEvalSupported: false,
    }).promise
    try {
      const pages: string[] = []
      for (let pageNumber = 1; pageNumber <= document.numPages; pageNumber += 1) {
        const page = await document.getPage(pageNumber)
        const content = await page.getTextContent()
        pages.push(content.items.map((item) => 'str' in item ? item.str : '').join(' '))
      }
      return assertReadableResumeText(pages.join('\n'))
    } finally {
      await document.cleanup()
      await document.destroy()
    }
  }
  const mammoth = await import('mammoth')
  return assertReadableResumeText((await mammoth.extractRawText({ buffer })).value)
}

export function isSupportedResumeType(type: string): type is SupportedResumeType {
  return SUPPORTED_RESUME_TYPES.includes(type as SupportedResumeType)
}
