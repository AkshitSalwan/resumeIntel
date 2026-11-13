0238  export function extractRequirements(jobDescription: string): Requirement[] {
0239    const normalized = normalizeText(jobDescription)
0240    const lines = splitLines(normalized)
0241    const requirements: Requirement[] = []
0242    const seen = new Set<string>()
0243    const importanceFor = (context: string): Requirement['importance'] =>
0244      /preferred|nice to have|bonus|plus|optional/i.test(context) ? 'preferred' : 'required'
0245    const addRequirement = (id: string, importance: Requirement['importance'], sourceText: string, uncertain = false, label = labelFor(id)) => {
0246      if (seen.has(id)) return
0247      seen.add(id)
0248      requirements.push({
0249        id,
0250        label,
0251        requirementText: sourceText,
0252        normalizedName: uncertain ? undefined : label,
0253        category: requirementCategory(id, sourceText),
0254        importance,
0255        weight: importance === 'required' ? 5 : 3,
0256        status: uncertain ? 'uncertain' : 'missing',
0257        sourceText,
0258        method: uncertain ? 'unmapped job-description requirement' : 'recognized taxonomy alias',
0259        explanation: uncertain ? 'This requirement appears in the job description but is not mapped to the supported skill taxonomy.' : undefined,
0260      })
0261    }
0262
0263    for (const line of lines) {
0264      const importance = importanceFor(line)
0265      const skills = extractSkills(line)
0266      for (const id of skills) addRequirement(id, importance, line)
0267      if (/^[-*•]\s+/.test(line) && !skills.length) {
0268        const label = line.replace(/^[-*•]\s+/, '').replace(/[.:]+$/, '').trim()
0269        if (label.split(/\s+/).length >= 2) addRequirement(stableUnmappedId(label), importance, line, true, label)
0270      }
0271    }
0272    if (!requirements.length) {
0273      for (const id of extractSkills(normalized)) addRequirement(id, importanceFor(normalized), normalized)
0274    }
0275    return requirements.map((item) => {
0276      if (item.id.startsWith('unmapped:')) return item
0277      const context = lines.find((line) => aliases[item.id].some((term) => termPattern(term).test(line))) ?? normalized
0278      const importance = importanceFor(context)
0279      return { ...item, requirementText: context, sourceText: context, importance, weight: importance === 'required' ? 5 : 3 }
0280    })
