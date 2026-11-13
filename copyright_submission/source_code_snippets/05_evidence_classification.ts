0283  export function classifyEvidence(resumeText: string, requirement: Requirement): Pick<Requirement, 'status' | 'evidence' | 'section' | 'source' | 'sourceLocation' | 'method' | 'explanation'> {
0284    if (requirement.id.startsWith('unmapped:')) {
0285      return {
0286        status: 'uncertain',
0287        source: 'Job description',
0288        sourceLocation: 'Requirement text',
0289        method: 'unsupported requirement',
0290        explanation: 'No supported taxonomy mapping is available, so this requirement cannot be matched reliably from resume text.',
0291      }
0292    }
0293    const found = findEvidence(resumeText, aliases[requirement.id] ?? [requirement.id])
0294    if (!found) {
0295      return {
0296        status: 'missing',
0297        source: 'No matching resume evidence found',
0298        sourceLocation: 'Resume text',
0299        method: 'complete-term search',
0300        explanation: `No recognizable resume evidence was found for ${requirement.label}.`,
0301      }
0302    }
0303    const isSkillsOnly = found.section === 'skills' || /^(skills|technical skills|competencies)\s*:/i.test(found.excerpt)
0304    if (isSkillsOnly || found.excerpt.split(/\s+/).length < 4) {
0305      return {
0306        status: 'partial',
0307        evidence: `Found “${found.term}” in: “${found.excerpt}”`,
0308        section: found.section,
0309        source: 'Resume skills section',
0310        sourceLocation: found.section,
0311        method: 'complete-term search with skills-list limitation',
0312        explanation: 'The term is listed, but the resume does not provide enough contextual evidence to treat it as demonstrated experience.',
0313      }
0314    }
0315    return {
0316      status: 'matched',
0317      evidence: `Found “${found.term}” in: “${found.excerpt}”`,
0318      section: found.section,
0319      source: found.section === 'projects' ? 'Resume project text' : found.section === 'experience' ? 'Resume experience or project text' : 'Resume contextual text',
0320      sourceLocation: found.section,
0321      method: 'complete-term contextual search',
0322      explanation: `The resume contains contextual evidence for ${requirement.label}. This indicates exposure in the cited section, not a guarantee of proficiency.`,
