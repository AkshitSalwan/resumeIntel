0001  import { normalizeText } from './analysis'
0002
0003  export const MAX_RESUME_BYTES = 10 * 1024 * 1024
0004  export const SUPPORTED_RESUME_TYPES = [
0005    'application/pdf',
0006    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
0007  ] as const
0008
0009  export type SupportedResumeType = (typeof SUPPORTED_RESUME_TYPES)[number]
0010
0011  export function validateResumeFile(file: Pick<File, 'name' | 'size' | 'type'>) {
0012    if (!SUPPORTED_RESUME_TYPES.includes(file.type as SupportedResumeType)) {
0013      return { ok: false as const, error: 'Only PDF and DOCX resumes are supported.' }
0014    }
0015    if (file.size === 0) return { ok: false as const, error: 'The resume file is empty.' }
0016    if (file.size > MAX_RESUME_BYTES) return { ok: false as const, error: 'Resume must be 10 MB or smaller.' }
0017    return { ok: true as const }
0018  }
0019
0020  export function hasValidFileSignature(type: string, buffer: Buffer) {
0021    if (type === 'application/pdf') return buffer.subarray(0, 5).toString('ascii') === '%PDF-'
0022    if (type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document') {
0023      return buffer.subarray(0, 2).toString('hex') === '504b'
0024    }
0025    return false
0026  }
0027
0028  export function normalizeExtractedResumeText(text: string) {
0029    return normalizeText(text).replace(/\u0000/g, '')
0030  }
0031
0032  export function assertReadableResumeText(text: string) {
0033    const normalized = normalizeExtractedResumeText(text)
0034    if (normalized.length < 40) throw new Error('The resume did not contain enough readable text.')
0035    return normalized
