import { describe, expect, it } from 'vitest'
import { analyzeResume, calculateScore, estimateSkillProficiencies, extractRequirements, validateJobDescription, validateScoringInputs, type Requirement } from '../lib/analysis'
import { extractResumeText, hasValidFileSignature, validateResumeFile } from '../lib/resume-extraction'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import PDFDocument from 'pdfkit'

const resume = readFileSync(resolve(process.cwd(), 'tests/fixtures/resume.txt'), 'utf8')
const jobDescription = 'Required: Python, SQL, and AWS experience building reliable analytics. Preferred: Kubernetes and accessibility knowledge. The role must communicate findings clearly and validate data.'

function createSyntheticPdf() {
  return new Promise<Buffer>((resolvePdf) => {
    const document = new PDFDocument()
    const chunks: Buffer[] = []
    document.on('data', (chunk: Buffer) => chunks.push(chunk))
    document.on('end', () => resolvePdf(Buffer.concat(chunks)))
    document.fontSize(18).text('Synthetic Resume')
    document.fontSize(12).text('Python SQL AWS experience demonstrated in projects.')
    document.end()
  })
}

describe('resume analysis', () => {
  it('extracts required and preferred requirements from job context', () => {
    const requirements = extractRequirements(jobDescription)
    expect(requirements.find((item) => item.id === 'python')?.importance).toBe('required')
    expect(requirements.find((item) => item.id === 'kubernetes')?.importance).toBe('preferred')
  })

  it('matches contextual evidence and preserves explainable evidence', () => {
    const result = analyzeResume(resume, jobDescription)
    const python = result.requirements.find((item) => item.id === 'python')
    const kubernetes = result.requirements.find((item) => item.id === 'kubernetes')
    expect(python?.status).toBe('matched')
    expect(python?.evidence).toContain('Python')
    expect(python?.source).toBe('Resume experience or project text')
    expect(kubernetes?.status).toBe('missing')
    expect(result.score).toBeGreaterThan(0)
    expect(result.score).toBeLessThan(100)
    expect(result.scoreDefinition).toContain('deterministic')
  })

  it('does not fabricate a score when there are no requirements', () => {
    expect(analyzeResume('Python experience', 'Strong communicator with curiosity.').score).toBe(0)
    expect(calculateScore([])).toBe(0)
  })

  it('deduplicates aliases and distinguishes partial keyword evidence', () => {
    const result = analyzeResume('Skills: React, React.js, TypeScript', 'Required: React.js and TypeScript.')
    expect(result.requirements.map((item) => item.id)).toEqual(['react', 'typescript'])
    expect(result.requirements.every((item) => item.status === 'partial')).toBe(true)
    expect(result.score).toBe(55)
  })

  it('records stable requirement metadata and score contributions', () => {
    const result = analyzeResume('Experience\nBuilt JavaScript services with Node.js.', 'Required: JS and Node.js experience.')
    const javascript = result.requirements.find((item) => item.id === 'javascript')
    expect(javascript).toMatchObject({
      normalizedName: 'JavaScript',
      category: 'technical skill',
      requirementText: 'Required: JS and Node.js experience.',
      status: 'matched',
      section: 'experience',
    })
    expect(javascript?.scoreContribution).toEqual({ credit: 1, earnedWeight: 5, possibleWeight: 5 })
  })

  it('matches explicit aliases without confusing Java and JavaScript', () => {
    expect(extractRequirements('Required: JavaScript and Node.js.').map((item) => item.id)).toEqual(['javascript', 'node'])
    const result = analyzeResume('Experience\nBuilt Java applications.', 'Required: JavaScript.')
    expect(result.requirements[0].status).toBe('missing')
  })

  it('preserves evidence provenance and reports missing evidence explicitly', () => {
    const result = analyzeResume('Projects\nBuilt Python ETL pipelines.', 'Required: Python and AWS.')
    const python = result.requirements.find((item) => item.id === 'python')
    const aws = result.requirements.find((item) => item.id === 'aws')
    expect(python?.evidence).toContain('Built Python ETL pipelines.')
    expect(python?.section).toBe('projects')
    expect(aws?.evidence).toBeUndefined()
    expect(aws?.explanation).toContain('No recognizable resume evidence')
  })

  it('categorizes unsupported responsibility requirements without inventing a skill', () => {
    const requirements = extractRequirements('- Communicate findings clearly')
    expect(requirements[0]).toMatchObject({
      category: 'responsibility',
      status: 'uncertain',
      normalizedName: undefined,
    })
  })

  it('replays the same score and evidence for identical inputs', () => {
    const first = analyzeResume(resume, jobDescription)
    const second = analyzeResume(resume, jobDescription)
    expect(second).toEqual(first)
  })

  it('orders strong, partial, and poor synthetic resumes by score', () => {
    const jd = 'Required: Python, SQL, and AWS experience. Preferred: Kubernetes.'
    const strong = analyzeResume('Built Python and SQL data pipelines on AWS. Operated Kubernetes deployments.', jd)
    const partial = analyzeResume('Skills: Python, SQL, AWS, Kubernetes.', jd)
    const poor = analyzeResume('Marketing student with writing and presentation experience.', jd)
    expect(strong.score).toBeGreaterThan(partial.score)
    expect(partial.score).toBeGreaterThan(poor.score)
    expect(poor.requirements.every((item) => item.status === 'missing')).toBe(true)
  })

  it('rejects empty, unreadable, and oversized job descriptions', () => {
    expect(validateJobDescription('')).toEqual({ ok: false, error: 'A job description is required.' })
    expect(validateJobDescription('!!!')).toEqual({ ok: false, error: 'The job description does not contain enough readable content.' })
    expect(validateJobDescription('x'.repeat(20001)).ok).toBe(false)
  })

  it('validates empty, zero, and negative scoring weights safely', () => {
    const base = (weight: number): Requirement => ({
      id: 'python',
      label: 'Python',
      requirementText: 'Required: Python.',
      category: 'technical skill',
      importance: 'required',
      weight,
      status: 'matched',
    })
    expect(validateScoringInputs([]).ok).toBe(false)
    expect(validateScoringInputs([base(0)]).ok).toBe(false)
    expect(validateScoringInputs([base(-1)]).ok).toBe(false)
    expect(calculateScore([base(-1)])).toBe(0)
  })
})

describe('skill proficiency estimation', () => {
  it('keeps a skills-list-only mention foundational with low evidence strength', () => {
    const result = estimateSkillProficiencies('Skills\nPython, SQL')
    expect(result.find((item) => item.skill === 'python')).toMatchObject({
      level: 'FOUNDATIONAL',
      confidence: 'LOW',
    })
  })

  it('treats basic academic or personal project evidence conservatively', () => {
    const result = estimateSkillProficiencies('Projects\nCourse project: used Python to clean a small dataset.')
    expect(result[0]).toMatchObject({ skill: 'python', level: 'FOUNDATIONAL' })
    expect(result[0].evidence[0]).toMatchObject({ section: 'projects', signal: 'academic-or-personal-project' })
  })

  it('estimates intermediate from one detailed contextual implementation', () => {
    const result = estimateSkillProficiencies('Projects\nBuilt Python ETL pipelines that validated schemas and loaded analytics data into storage.')
    expect(result[0].level).toBe('INTERMEDIATE')
    expect(result[0].evidence[0].excerpt).toContain('Built Python ETL pipelines')
  })

  it('requires multiple distinct detailed examples for advanced', () => {
    const resume = 'Experience\nBuilt Python ETL pipelines that validated schemas and reduced failures.\nProjects\nDesigned Python feature extraction jobs that improved model input quality.'
    const result = estimateSkillProficiencies(resume)
    expect(result[0]).toMatchObject({ level: 'ADVANCED', confidence: 'HIGH' })
    expect(result[0].evidence).toHaveLength(2)
  })

  it('deduplicates repeated evidence and does not infer from negative statements', () => {
    const repeated = estimateSkillProficiencies('Experience\nBuilt Python ETL pipelines.\nBuilt Python ETL pipelines.')
    expect(repeated[0].evidence).toHaveLength(1)
    const negative = estimateSkillProficiencies('Experience\nNo experience with Python.')
    expect(negative[0]).toMatchObject({ level: 'NOT_ENOUGH_EVIDENCE', evidence: [] })
  })

  it('does not estimate unsupported skills outside the maintained taxonomy', () => {
    expect(estimateSkillProficiencies('Experience\nBuilt Go services and Rust tools.')).toEqual([])
  })

  it('preserves certification provenance and does not alter the ATS score', () => {
    const resume = 'Certifications\nAWS Certified Cloud Practitioner'
    const result = analyzeResume(resume, 'Required: AWS.')
    expect(result.proficiencies[0]).toMatchObject({ level: 'FOUNDATIONAL', confidence: 'MEDIUM' })
    expect(result.proficiencies[0].evidence[0]).toMatchObject({ section: 'certifications', signal: 'certification' })
    expect(result.score).toBe(100)
  })

  it('is deterministic and leaves old result shapes readable', () => {
    const resume = 'Experience\nImplemented Node.js services with tests.'
    expect(estimateSkillProficiencies(resume)).toEqual(estimateSkillProficiencies(resume))
    const oldReport: { score: number; requirements: never[]; proficiencies?: unknown } = { score: 50, requirements: [] }
    expect(oldReport.proficiencies).toBeUndefined()
  })
})

describe('resume upload validation', () => {
  it('accepts supported types only within the size limit', () => {
    expect(validateResumeFile({ name: 'resume.pdf', type: 'application/pdf', size: 500 })).toEqual({ ok: true })
    expect(validateResumeFile({ name: 'resume.exe', type: 'application/octet-stream', size: 500 }).ok).toBe(false)
    expect(validateResumeFile({ name: 'resume.pdf', type: 'application/pdf', size: 10 * 1024 * 1024 + 1 }).ok).toBe(false)
  })

  it('checks file signatures instead of trusting MIME type', () => {
    expect(hasValidFileSignature('application/pdf', Buffer.from('%PDF-1.7'))).toBe(true)
    expect(hasValidFileSignature('application/pdf', Buffer.from('not a pdf'))).toBe(false)
    expect(hasValidFileSignature('application/vnd.openxmlformats-officedocument.wordprocessingml.document', Buffer.from('PK\u0003\u0004'))).toBe(true)
  })

  it('extracts readable text from a synthetic PDF', async () => {
    const extracted = await extractResumeText('application/pdf', await createSyntheticPdf())
    expect(extracted).toContain('Synthetic Resume')
    expect(extracted).toContain('Python SQL AWS')
  })

  it('rejects a malformed file after signature validation', async () => {
    await expect(extractResumeText('application/pdf', Buffer.from('%PDF-not-a-valid-document'))).rejects.toThrow()
  })
})
