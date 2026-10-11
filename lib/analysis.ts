export type EvidenceStatus = 'matched' | 'partial' | 'missing' | 'uncertain'
export type RequirementCategory = 'technical skill' | 'tool' | 'qualification' | 'responsibility' | 'other'
export type ResumeSection = 'skills' | 'experience' | 'projects' | 'education' | 'certifications' | 'other'
export type ProficiencyLevel = 'NOT_ENOUGH_EVIDENCE' | 'FOUNDATIONAL' | 'INTERMEDIATE' | 'ADVANCED'
export type EvidenceConfidence = 'LOW' | 'MEDIUM' | 'HIGH'

export type ScoreContribution = {
  credit: number
  earnedWeight: number
  possibleWeight: number
}

export type Requirement = {
  id: string
  label: string
  requirementText: string
  normalizedName?: string
  category: RequirementCategory
  importance: 'required' | 'preferred'
  weight: number
  status: EvidenceStatus
  sourceText?: string
  evidence?: string
  section?: ResumeSection
  source?: string
  sourceLocation?: string
  method?: string
  explanation?: string
  scoreContribution?: ScoreContribution
}

export type ProficiencyEvidence = {
  excerpt: string
  section: ResumeSection
  sourceLocation: string
  signal: 'skills-list' | 'academic-or-personal-project' | 'implementation-detail' | 'professional-responsibility' | 'certification'
}

export type SkillProficiency = {
  skill: string
  normalizedName: string
  level: ProficiencyLevel
  confidence: EvidenceConfidence
  explanation: string
  evidence: ProficiencyEvidence[]
  uncertainty: string
}

export const TAXONOMY_VERSION = '2026-10-11'

/**
 * Canonical skill IDs and their explicit, complete-term aliases.
 * Related technologies are intentionally separate unless listed together.
 */
export const aliases: Record<string, string[]> = {
  javascript: ['javascript', 'js', 'ecmascript'],
  react: ['react', 'react.js', 'reactjs'],
  typescript: ['typescript', 'ts'],
  next: ['next.js', 'nextjs', 'next js'],
  node: ['node.js', 'nodejs', 'node'],
  postgresql: ['postgresql', 'postgres'],
  testing: ['testing', 'jest', 'vitest', 'playwright'],
  accessibility: ['accessibility', 'wcag', 'aria'],
  python: ['python'],
  sql: ['sql'],
  aws: ['aws', 'amazon web services'],
  kubernetes: ['kubernetes', 'k8s'],
}

const categoryBySkill: Record<string, RequirementCategory> = {
  javascript: 'technical skill',
  react: 'technical skill',
  typescript: 'technical skill',
  next: 'tool',
  node: 'tool',
  postgresql: 'tool',
  testing: 'technical skill',
  accessibility: 'qualification',
  python: 'technical skill',
  sql: 'technical skill',
  aws: 'tool',
  kubernetes: 'tool',
}

export const scoreDefinition = 'A deterministic, weighted job-description match score based on resume evidence. Required requirements have weight 5, preferred requirements have weight 3, and the existing documented credits are matched 1.00, partial 0.55, uncertain 0.35, and missing 0.00. It is not an employer ATS score, hiring probability, or interview prediction.'
export const SCORE_WEIGHTS = { matched: 1, partial: 0.55, uncertain: 0.35, missing: 0 } as const
export const MAX_JOB_DESCRIPTION_LENGTH = 20000

export function validateJobDescription(value: string) {
  const normalized = normalizeText(value)
  if (!normalized) return { ok: false as const, error: 'A job description is required.' }
  if (normalized.length > MAX_JOB_DESCRIPTION_LENGTH) return { ok: false as const, error: 'Job descriptions must be 20,000 characters or fewer.' }
  if (normalized.replace(/[\W_]/g, '').length < 20) return { ok: false as const, error: 'The job description does not contain enough readable content.' }
  return { ok: true as const, value: normalized }
}

export function normalizeText(text: string) {
  return text.normalize('NFKC').replace(/[\t ]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function termPattern(term: string) {
  const prefix = term.length <= 2 ? '(?<![A-Za-z0-9.])' : '(?<![A-Za-z0-9])'
  return new RegExp(`${prefix}${escapeRegExp(term)}(?![A-Za-z0-9])`, 'i')
}

function splitLines(text: string) {
  return normalizeText(text).split(/\n+|(?<=[.!?])\s+/).map((line) => line.trim()).filter(Boolean)
}

function sectionForHeading(line: string): ResumeSection | undefined {
  const heading = line.replace(/[:\-]+$/, '').trim().toLowerCase()
  if (/^(skills|technical skills|competencies|technologies)$/.test(heading)) return 'skills'
  if (/^(experience|work experience|professional experience|employment)$/.test(heading)) return 'experience'
  if (/^(projects|selected projects)$/.test(heading)) return 'projects'
  if (/^(education|academic background)$/.test(heading)) return 'education'
  if (/^(certifications|certificates)$/.test(heading)) return 'certifications'
  return undefined
}

function findEvidence(text: string, terms: string[]) {
  const lines = splitLines(text)
  let section: ResumeSection = 'other'
  for (const line of lines) {
    const headingSection = sectionForHeading(line)
    if (headingSection) {
      section = headingSection
      continue
    }

    const term = terms.find((candidate) => termPattern(candidate).test(line))
    if (term) return { term, excerpt: line.trim(), section }
  }
  return undefined
}

function proficiencySignal(section: ResumeSection, excerpt: string): ProficiencyEvidence['signal'] {
  if (section === 'skills') return 'skills-list'
  if (section === 'projects') return /school|academic|course|class|university|college/i.test(excerpt) ? 'academic-or-personal-project' : 'implementation-detail'
  if (section === 'experience') return /\b(build|built|design|designed|develop|developed|implement|implemented|deploy|deployed|architect|maintain|maintained|lead|led|optimiz|integrat|test|tested|migrat|automate|reduc|increas|improv)\w*/i.test(excerpt)
    ? 'professional-responsibility'
    : 'implementation-detail'
  if (section === 'certifications') return 'certification'
  return section === 'education' ? 'academic-or-personal-project' : 'implementation-detail'
}

function collectProficiencyEvidence(text: string, terms: string[]) {
  const lines = splitLines(text)
  let section: ResumeSection = 'other'
  const seen = new Set<string>()
  const evidence: ProficiencyEvidence[] = []
  for (const line of lines) {
    const headingSection = sectionForHeading(line)
    if (headingSection) {
      section = headingSection
      continue
    }
    if (/\b(no experience|not familiar|without experience|never used|do not use)\b/i.test(line)) continue
    if (!terms.some((term) => termPattern(term).test(line))) continue
    const excerpt = line.trim()
    const key = `${section}:${excerpt.toLowerCase()}`
    if (seen.has(key)) continue
    seen.add(key)
    evidence.push({
      excerpt,
      section,
      sourceLocation: section,
      signal: proficiencySignal(section, excerpt),
    })
  }
  return evidence
}

export const proficiencyDefinition = 'Deterministic evidence-supported estimates: NOT_ENOUGH_EVIDENCE means no usable evidence; FOUNDATIONAL means a skills-list, education, certification, or basic exposure signal; INTERMEDIATE means one contextual implementation or responsibility signal; ADVANCED requires at least two distinct detailed implementation or responsibility signals across relevant resume evidence. Confidence is an evidence-strength label, not a statistically calibrated probability.'

export function estimateSkillProficiencies(resumeText: string): SkillProficiency[] {
  return extractSkills(resumeText).map((skill) => {
    const evidence = collectProficiencyEvidence(resumeText, aliases[skill])
    const normalizedName = labelFor(skill)
    const contextual = evidence.filter((item) => item.signal === 'implementation-detail' || item.signal === 'professional-responsibility')
    const strong = contextual.filter((item) => item.excerpt.split(/\s+/).length >= 7)
    let level: ProficiencyLevel = 'NOT_ENOUGH_EVIDENCE'
    let confidence: EvidenceConfidence = 'LOW'
    let explanation = `No usable evidence was found for ${normalizedName}.`
    let uncertainty = `The resume does not provide enough source-grounded evidence to estimate ${normalizedName}. This is not evidence that the skill is absent.`
    if (evidence.length > 0) {
      if (strong.length >= 2 && new Set(strong.map((item) => `${item.section}:${item.excerpt.toLowerCase()}`)).size >= 2) {
        level = 'ADVANCED'
        confidence = 'HIGH'
        explanation = `Multiple distinct detailed implementation or responsibility examples support an advanced evidence estimate for ${normalizedName}.`
        uncertainty = 'This remains an estimate from resume evidence, not verified real-world competence.'
      } else if (strong.length >= 1) {
        level = 'INTERMEDIATE'
        confidence = 'MEDIUM'
        explanation = `A detailed contextual example supports an intermediate evidence estimate for ${normalizedName}.`
        uncertainty = 'The resume provides one detailed example; breadth and depth beyond that example are unknown.'
      } else {
        level = 'FOUNDATIONAL'
        confidence = evidence.some((item) => item.signal === 'skills-list') ? 'LOW' : 'MEDIUM'
        explanation = `The resume contains ${evidence[0].signal === 'skills-list' ? 'a skills-list mention' : 'basic exposure evidence'} for ${normalizedName}, but not enough detail for a higher estimate.`
        uncertainty = 'A mention, education, certification, or basic exposure signal does not establish professional proficiency.'
      }
    }
    return { skill, normalizedName, level, confidence, explanation, evidence, uncertainty }
  })
}

export function extractSkills(text: string) {
  const normalized = normalizeText(text)
  return Object.entries(aliases)
    .filter(([, terms]) => terms.some((term) => termPattern(term).test(normalized)))
    .map(([skill]) => skill)
}

function labelFor(id: string) {
  if (id === 'javascript') return 'JavaScript'
  if (id === 'next') return 'Next.js'
  if (id === 'node') return 'Node.js'
  return id.charAt(0).toUpperCase() + id.slice(1)
}

function requirementCategory(id: string, sourceText = ''): RequirementCategory {
  if (id.startsWith('unmapped:')) {
    if (/\b(degree|bachelor|master|certif|qualification)\b/i.test(sourceText)) return 'qualification'
    if (/^(?:[-*•]\s*)?(?:build|design|develop|lead|manage|communicate|collaborate|deliver|analy[sz]e|validate|maintain|support)\b/i.test(sourceText.trim())) return 'responsibility'
    return 'other'
  }
  return categoryBySkill[id] ?? 'other'
}

function stableUnmappedId(label: string) {
  return `unmapped:${label.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 48)}`
}

export function extractRequirements(jobDescription: string): Requirement[] {
  const normalized = normalizeText(jobDescription)
  const lines = splitLines(normalized)
  const requirements: Requirement[] = []
  const seen = new Set<string>()
  const importanceFor = (context: string): Requirement['importance'] =>
    /preferred|nice to have|bonus|plus|optional/i.test(context) ? 'preferred' : 'required'
  const addRequirement = (id: string, importance: Requirement['importance'], sourceText: string, uncertain = false, label = labelFor(id)) => {
    if (seen.has(id)) return
    seen.add(id)
    requirements.push({
      id,
      label,
      requirementText: sourceText,
      normalizedName: uncertain ? undefined : label,
      category: requirementCategory(id, sourceText),
      importance,
      weight: importance === 'required' ? 5 : 3,
      status: uncertain ? 'uncertain' : 'missing',
      sourceText,
      method: uncertain ? 'unmapped job-description requirement' : 'recognized taxonomy alias',
      explanation: uncertain ? 'This requirement appears in the job description but is not mapped to the supported skill taxonomy.' : undefined,
    })
  }

  for (const line of lines) {
    const importance = importanceFor(line)
    const skills = extractSkills(line)
    for (const id of skills) addRequirement(id, importance, line)
    if (/^[-*•]\s+/.test(line) && !skills.length) {
      const label = line.replace(/^[-*•]\s+/, '').replace(/[.:]+$/, '').trim()
      if (label.split(/\s+/).length >= 2) addRequirement(stableUnmappedId(label), importance, line, true, label)
    }
  }
  if (!requirements.length) {
    for (const id of extractSkills(normalized)) addRequirement(id, importanceFor(normalized), normalized)
  }
  return requirements.map((item) => {
    if (item.id.startsWith('unmapped:')) return item
    const context = lines.find((line) => aliases[item.id].some((term) => termPattern(term).test(line))) ?? normalized
    const importance = importanceFor(context)
    return { ...item, requirementText: context, sourceText: context, importance, weight: importance === 'required' ? 5 : 3 }
  })
}

export function classifyEvidence(resumeText: string, requirement: Requirement): Pick<Requirement, 'status' | 'evidence' | 'section' | 'source' | 'sourceLocation' | 'method' | 'explanation'> {
  if (requirement.id.startsWith('unmapped:')) {
    return {
      status: 'uncertain',
      source: 'Job description',
      sourceLocation: 'Requirement text',
      method: 'unsupported requirement',
      explanation: 'No supported taxonomy mapping is available, so this requirement cannot be matched reliably from resume text.',
    }
  }
  const found = findEvidence(resumeText, aliases[requirement.id] ?? [requirement.id])
  if (!found) {
    return {
      status: 'missing',
      source: 'No matching resume evidence found',
      sourceLocation: 'Resume text',
      method: 'complete-term search',
      explanation: `No recognizable resume evidence was found for ${requirement.label}.`,
    }
  }
  const isSkillsOnly = found.section === 'skills' || /^(skills|technical skills|competencies)\s*:/i.test(found.excerpt)
  if (isSkillsOnly || found.excerpt.split(/\s+/).length < 4) {
    return {
      status: 'partial',
      evidence: `Found “${found.term}” in: “${found.excerpt}”`,
      section: found.section,
      source: 'Resume skills section',
      sourceLocation: found.section,
      method: 'complete-term search with skills-list limitation',
      explanation: 'The term is listed, but the resume does not provide enough contextual evidence to treat it as demonstrated experience.',
    }
  }
  return {
    status: 'matched',
    evidence: `Found “${found.term}” in: “${found.excerpt}”`,
    section: found.section,
    source: found.section === 'projects' ? 'Resume project text' : found.section === 'experience' ? 'Resume experience or project text' : 'Resume contextual text',
    sourceLocation: found.section,
    method: 'complete-term contextual search',
    explanation: `The resume contains contextual evidence for ${requirement.label}. This indicates exposure in the cited section, not a guarantee of proficiency.`,
  }
}

export function validateScoringInputs(items: Requirement[]) {
  if (!items.length) return { ok: false as const, error: 'At least one requirement is needed to calculate a score.' }
  if (items.some((item) => !Number.isFinite(item.weight) || item.weight < 0)) return { ok: false as const, error: 'Requirement weights must be finite and non-negative.' }
  if (items.reduce((sum, item) => sum + item.weight, 0) <= 0) return { ok: false as const, error: 'Requirement weights must have a total greater than zero.' }
  return { ok: true as const }
}

export function analyzeResume(resumeText: string, jobDescription: string) {
  const requirements = extractRequirements(jobDescription).map((item) => ({ ...item, ...classifyEvidence(resumeText, item) }))
  const scoreBreakdown = calculateScoreBreakdown(requirements)
  const detailedRequirements = requirements.map((item) => ({
    ...item,
    scoreContribution: {
      credit: SCORE_WEIGHTS[item.status],
      earnedWeight: item.weight * SCORE_WEIGHTS[item.status],
      possibleWeight: item.weight,
    },
  }))
  return { taxonomyVersion: TAXONOMY_VERSION, requirements: detailedRequirements, proficiencies: estimateSkillProficiencies(resumeText), proficiencyDefinition, score: scoreBreakdown.score, scoreBreakdown, scoreDefinition }
}

export function calculateScore(items: Requirement[]) {
  return calculateScoreBreakdown(items).score
}

export function calculateScoreBreakdown(items: Requirement[]) {
  const validation = validateScoringInputs(items)
  const required = items.filter((item) => item.importance === 'required')
  const preferred = items.filter((item) => item.importance === 'preferred')
  if (!validation.ok) {
    return {
      score: 0,
      earnedWeight: 0,
      maximumWeight: 0,
      required: summarizeStatuses(required),
      preferred: summarizeStatuses(preferred),
    }
  }
  const max = items.reduce((sum, item) => sum + item.weight, 0)
  const earned = items.reduce((sum, item) => sum + item.weight * SCORE_WEIGHTS[item.status], 0)
  return {
    score: Math.round((earned / max) * 100),
    earnedWeight: earned,
    maximumWeight: max,
    required: summarizeStatuses(required),
    preferred: summarizeStatuses(preferred),
  }
}

function summarizeStatuses(items: Requirement[]) {
  const possibleWeight = items.reduce((sum, item) => sum + Math.max(0, item.weight), 0)
  const earnedWeight = items.reduce((sum, item) => sum + Math.max(0, item.weight) * SCORE_WEIGHTS[item.status], 0)
  return {
    count: items.length,
    matched: items.filter((item) => item.status === 'matched').length,
    partial: items.filter((item) => item.status === 'partial').length,
    missing: items.filter((item) => item.status === 'missing').length,
    uncertain: items.filter((item) => item.status === 'uncertain').length,
    earnedWeight,
    possibleWeight,
    weightedScore: possibleWeight ? Math.round((earnedWeight / possibleWeight) * 100) : 0,
  }
}

export function getCounterfactualScore(items: Requirement[], requirementId: string) {
  return calculateScore(items.map((item) => item.id === requirementId ? { ...item, status: 'matched' } : item))
}

export function getRecommendations(result: { requirements: Requirement[] }) {
  return result.requirements.filter((item) => item.status !== 'matched').map((item) => ({
    requirement: item.label,
    rationale: item.explanation ?? 'Additional evidence may be useful.',
    impact: `Hypothetical score: ${getCounterfactualScore(result.requirements, item.id)}/100`,
  }))
}
