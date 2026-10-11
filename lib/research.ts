import { analyzeResume } from './analysis'

export type ExperimentKind = 'counterfactual' | 'robustness' | 'baseline'

export type ExperimentConfig = {
  kind: ExperimentKind
  name: string
  resumeText: string
  jobDescription: string
  transformation?: 'remove_section' | 'reorder_sections' | 'paraphrase_bullets'
  baseline?: 'keyword' | 'proposed_method'
}

export type ExperimentResult = {
  executed: true
  kind: ExperimentKind
  score: number
  metrics: Record<string, number>
  output: Record<string, unknown>
}

const stopWords = new Set(['a', 'an', 'and', 'are', 'as', 'be', 'for', 'from', 'in', 'is', 'of', 'on', 'or', 'the', 'to', 'with'])

export function tokenize(value: string) {
  return [...new Set(value.toLowerCase().match(/[a-z0-9][a-z0-9+#.-]*/g) ?? [])].filter((token) => !stopWords.has(token))
}

export function keywordBaseline(resumeText: string, jobDescription: string) {
  const resumeTokens = new Set(tokenize(resumeText))
  const jobTokens = tokenize(jobDescription)
  const matched = jobTokens.filter((token) => resumeTokens.has(token))
  const score = jobTokens.length ? Math.round((matched.length / jobTokens.length) * 100) : 0
  return { score, matched: [...new Set(matched)], totalTerms: jobTokens.length }
}

export function transformResume(resumeText: string, transformation: NonNullable<ExperimentConfig['transformation']>) {
  if (transformation === 'remove_section') return resumeText.replace(/\b(education|certifications|skills)\b[\s\S]*?(?=\n[A-Z][^\n]{2,40}\n|$)/i, '').trim()
  if (transformation === 'reorder_sections') return `${resumeText.split(/\n{2,}/).reverse().join('\n\n').trim()}\n`
  return resumeText.split(/\n/).map((line) => line.replace(/\b(led|built|created|managed)\b/gi, 'contributed to')).join('\n')
}

export function runExperiment(config: ExperimentConfig): ExperimentResult {
  if (!config.resumeText.trim() || !config.jobDescription.trim()) throw new Error('Resume text and job description are required')
  if (config.kind === 'baseline') {
    const result = config.baseline === 'keyword' ? keywordBaseline(config.resumeText, config.jobDescription) : analyzeResume(config.resumeText, config.jobDescription)
    const score = result.score
    const matchedTerms = 'matched' in result ? result.matched.length : result.requirements.filter((item) => item.status === 'matched').length
    return { executed: true, kind: 'baseline', score, metrics: { score, matchedTerms }, output: result }
  }

  const baseline = analyzeResume(config.resumeText, config.jobDescription)
  const transformedText = transformResume(config.resumeText, config.transformation ?? 'reorder_sections')
  const transformed = analyzeResume(transformedText, config.jobDescription)
  const delta = transformed.score - baseline.score
  return { executed: true, kind: config.kind, score: transformed.score, metrics: { baselineScore: baseline.score, transformedScore: transformed.score, scoreDelta: delta, qualificationPreserved: transformed.requirements.filter((item) => item.status === 'matched').length >= Math.max(0, baseline.requirements.filter((item) => item.status === 'matched').length - 1) ? 1 : 0 }, output: { baseline, transformed, transformation: config.transformation } }
}
