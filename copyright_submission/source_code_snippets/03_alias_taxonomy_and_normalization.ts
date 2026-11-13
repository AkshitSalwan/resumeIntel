0049  export const TAXONOMY_VERSION = '2026-10-11'
0050
0051  /**
0052   * Canonical skill IDs and their explicit, complete-term aliases.
0053   * Related technologies are intentionally separate unless listed together.
0054   */
0055  export const aliases: Record<string, string[]> = {
0056    javascript: ['javascript', 'js', 'ecmascript'],
0057    react: ['react', 'react.js', 'reactjs'],
0058    typescript: ['typescript', 'ts'],
0059    next: ['next.js', 'nextjs', 'next js'],
0060    node: ['node.js', 'nodejs', 'node'],
0061    postgresql: ['postgresql', 'postgres'],
0062    testing: ['testing', 'jest', 'vitest', 'playwright'],
0063    accessibility: ['accessibility', 'wcag', 'aria'],
0064    python: ['python'],
0065    sql: ['sql'],
0066    aws: ['aws', 'amazon web services'],
0067    kubernetes: ['kubernetes', 'k8s'],
0068  }
0069
0070  const categoryBySkill: Record<string, RequirementCategory> = {
0071    javascript: 'technical skill',
0072    react: 'technical skill',
0073    typescript: 'technical skill',
0074    next: 'tool',
0075    node: 'tool',
0076    postgresql: 'tool',
0077    testing: 'technical skill',
0078    accessibility: 'qualification',
0079    python: 'technical skill',
0080    sql: 'technical skill',
0081    aws: 'tool',
0082    kubernetes: 'tool',
0083  }
0084
0085  export const scoreDefinition = 'A deterministic, weighted job-description match score based on resume evidence. Required requirements have weight 5, preferred requirements have weight 3, and the existing documented credits are matched 1.00, partial 0.55, uncertain 0.35, and missing 0.00. It is not an employer ATS score, hiring probability, or interview prediction.'
0086  export const SCORE_WEIGHTS = { matched: 1, partial: 0.55, uncertain: 0.35, missing: 0 } as const
0087  export const MAX_JOB_DESCRIPTION_LENGTH = 20000
0088
0089  export function validateJobDescription(value: string) {
0090    const normalized = normalizeText(value)
0091    if (!normalized) return { ok: false as const, error: 'A job description is required.' }
0092    if (normalized.length > MAX_JOB_DESCRIPTION_LENGTH) return { ok: false as const, error: 'Job descriptions must be 20,000 characters or fewer.' }
0093    if (normalized.replace(/[\W_]/g, '').length < 20) return { ok: false as const, error: 'The job description does not contain enough readable content.' }
0094    return { ok: true as const, value: normalized }
0095  }
0096
0097  export function normalizeText(text: string) {
0098    return text.normalize('NFKC').replace(/[\t ]+/g, ' ').replace(/\n{3,}/g, '\n\n').trim()
0099  }
0100
0101  function escapeRegExp(value: string) {
0102    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
0103  }
0104
0105  function termPattern(term: string) {
0106    const prefix = term.length <= 2 ? '(?<![A-Za-z0-9.])' : '(?<![A-Za-z0-9])'
0107    return new RegExp(`${prefix}${escapeRegExp(term)}(?![A-Za-z0-9])`, 'i')
0108  }
