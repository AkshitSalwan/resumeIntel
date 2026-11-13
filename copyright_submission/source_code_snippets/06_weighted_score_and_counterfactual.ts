0333  export function analyzeResume(resumeText: string, jobDescription: string) {
0334    const requirements = extractRequirements(jobDescription).map((item) => ({ ...item, ...classifyEvidence(resumeText, item) }))
0335    const scoreBreakdown = calculateScoreBreakdown(requirements)
0336    const detailedRequirements = requirements.map((item) => ({
0337      ...item,
0338      scoreContribution: {
0339        credit: SCORE_WEIGHTS[item.status],
0340        earnedWeight: item.weight * SCORE_WEIGHTS[item.status],
0341        possibleWeight: item.weight,
0342      },
0343    }))
0344    return { taxonomyVersion: TAXONOMY_VERSION, requirements: detailedRequirements, proficiencies: estimateSkillProficiencies(resumeText), proficiencyDefinition, score: scoreBreakdown.score, scoreBreakdown, scoreDefinition }
0345  }
0346
0347  export function calculateScore(items: Requirement[]) {
0348    return calculateScoreBreakdown(items).score
0349  }
0350
0351  export function calculateScoreBreakdown(items: Requirement[]) {
0352    const validation = validateScoringInputs(items)
0353    const required = items.filter((item) => item.importance === 'required')
0354    const preferred = items.filter((item) => item.importance === 'preferred')
0355    if (!validation.ok) {
0356      return {
0357        score: 0,
0358        earnedWeight: 0,
0359        maximumWeight: 0,
0360        required: summarizeStatuses(required),
0361        preferred: summarizeStatuses(preferred),
0362      }
0363    }
0364    const max = items.reduce((sum, item) => sum + item.weight, 0)
0365    const earned = items.reduce((sum, item) => sum + item.weight * SCORE_WEIGHTS[item.status], 0)
0366    return {
0367      score: Math.round((earned / max) * 100),
0368      earnedWeight: earned,
0369      maximumWeight: max,
0370      required: summarizeStatuses(required),
0371      preferred: summarizeStatuses(preferred),
0372    }
