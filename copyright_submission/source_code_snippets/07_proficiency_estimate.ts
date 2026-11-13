0177  export const proficiencyDefinition = 'Deterministic evidence-supported estimates: NOT_ENOUGH_EVIDENCE means no usable evidence; FOUNDATIONAL means a skills-list, education, certification, or basic exposure signal; INTERMEDIATE means one contextual implementation or responsibility signal; ADVANCED requires at least two distinct detailed implementation or responsibility signals across relevant resume evidence. Confidence is an evidence-strength label, not a statistically calibrated probability.'
0178
0179  export function estimateSkillProficiencies(resumeText: string): SkillProficiency[] {
0180    return extractSkills(resumeText).map((skill) => {
0181      const evidence = collectProficiencyEvidence(resumeText, aliases[skill])
0182      const normalizedName = labelFor(skill)
0183      const contextual = evidence.filter((item) => item.signal === 'implementation-detail' || item.signal === 'professional-responsibility')
0184      const strong = contextual.filter((item) => item.excerpt.split(/\s+/).length >= 7)
0185      let level: ProficiencyLevel = 'NOT_ENOUGH_EVIDENCE'
0186      let confidence: EvidenceConfidence = 'LOW'
0187      let explanation = `No usable evidence was found for ${normalizedName}.`
0188      let uncertainty = `The resume does not provide enough source-grounded evidence to estimate ${normalizedName}. This is not evidence that the skill is absent.`
0189      if (evidence.length > 0) {
0190        if (strong.length >= 2 && new Set(strong.map((item) => `${item.section}:${item.excerpt.toLowerCase()}`)).size >= 2) {
0191          level = 'ADVANCED'
0192          confidence = 'HIGH'
0193          explanation = `Multiple distinct detailed implementation or responsibility examples support an advanced evidence estimate for ${normalizedName}.`
0194          uncertainty = 'This remains an estimate from resume evidence, not verified real-world competence.'
0195        } else if (strong.length >= 1) {
0196          level = 'INTERMEDIATE'
0197          confidence = 'MEDIUM'
0198          explanation = `A detailed contextual example supports an intermediate evidence estimate for ${normalizedName}.`
0199          uncertainty = 'The resume provides one detailed example; breadth and depth beyond that example are unknown.'
0200        } else {
0201          level = 'FOUNDATIONAL'
0202          confidence = evidence.some((item) => item.signal === 'skills-list') ? 'LOW' : 'MEDIUM'
0203          explanation = `The resume contains ${evidence[0].signal === 'skills-list' ? 'a skills-list mention' : 'basic exposure evidence'} for ${normalizedName}, but not enough detail for a higher estimate.`
0204          uncertainty = 'A mention, education, certification, or basic exposure signal does not establish professional proficiency.'
0205        }
0206      }
0207      return { skill, normalizedName, level, confidence, explanation, evidence, uncertainty }
0208    })
