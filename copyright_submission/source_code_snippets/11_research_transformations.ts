0014  export type ExperimentResult = {
0015    executed: true
0016    kind: ExperimentKind
0017    score: number
0018    metrics: Record<string, number>
0019    output: Record<string, unknown>
0020  }
0021
0022  const stopWords = new Set(['a', 'an', 'and', 'are', 'as', 'be', 'for', 'from', 'in', 'is', 'of', 'on', 'or', 'the', 'to', 'with'])
0023
0024  export function tokenize(value: string) {
0025    return [...new Set(value.toLowerCase().match(/[a-z0-9][a-z0-9+#.-]*/g) ?? [])].filter((token) => !stopWords.has(token))
0026  }
0027
0028  export function keywordBaseline(resumeText: string, jobDescription: string) {
0029    const resumeTokens = new Set(tokenize(resumeText))
0030    const jobTokens = tokenize(jobDescription)
0031    const matched = jobTokens.filter((token) => resumeTokens.has(token))
0032    const score = jobTokens.length ? Math.round((matched.length / jobTokens.length) * 100) : 0
0033    return { score, matched: [...new Set(matched)], totalTerms: jobTokens.length }
0034  }
0035
0036  export function transformResume(resumeText: string, transformation: NonNullable<ExperimentConfig['transformation']>) {
0037    if (transformation === 'remove_section') return resumeText.replace(/\b(education|certifications|skills)\b[\s\S]*?(?=\n[A-Z][^\n]{2,40}\n|$)/i, '').trim()
0038    if (transformation === 'reorder_sections') return `${resumeText.split(/\n{2,}/).reverse().join('\n\n').trim()}\n`
0039    return resumeText.split(/\n/).map((line) => line.replace(/\b(led|built|created|managed)\b/gi, 'contributed to')).join('\n')
0040  }
0041
0042  export function runExperiment(config: ExperimentConfig): ExperimentResult {
0043    if (!config.resumeText.trim() || !config.jobDescription.trim()) throw new Error('Resume text and job description are required')
0044    if (config.kind === 'baseline') {
0045      const result = config.baseline === 'keyword' ? keywordBaseline(config.resumeText, config.jobDescription) : analyzeResume(config.resumeText, config.jobDescription)
0046      const score = result.score
0047      const matchedTerms = 'matched' in result ? result.matched.length : result.requirements.filter((item) => item.status === 'matched').length
0048      return { executed: true, kind: 'baseline', score, metrics: { score, matchedTerms }, output: result }
0049    }
0050
0051    const baseline = analyzeResume(config.resumeText, config.jobDescription)
0052    const transformedText = transformResume(config.resumeText, config.transformation ?? 'reorder_sections')
0053    const transformed = analyzeResume(transformedText, config.jobDescription)
0054    const delta = transformed.score - baseline.score
0055    return { executed: true, kind: config.kind, score: transformed.score, metrics: { baselineScore: baseline.score, transformedScore: transformed.score, scoreDelta: delta, qualificationPreserved: transformed.requirements.filter((item) => item.status === 'matched').length >= Math.max(0, baseline.requirements.filter((item) => item.status === 'matched').length - 1) ? 1 : 0 }, output: { baseline, transformed, transformation: config.transformation } }
