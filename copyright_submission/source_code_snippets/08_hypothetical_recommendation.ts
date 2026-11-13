0377    const earnedWeight = items.reduce((sum, item) => sum + Math.max(0, item.weight) * SCORE_WEIGHTS[item.status], 0)
0378    return {
0379      count: items.length,
0380      matched: items.filter((item) => item.status === 'matched').length,
0381      partial: items.filter((item) => item.status === 'partial').length,
0382      missing: items.filter((item) => item.status === 'missing').length,
0383      uncertain: items.filter((item) => item.status === 'uncertain').length,
0384      earnedWeight,
0385      possibleWeight,
0386      weightedScore: possibleWeight ? Math.round((earnedWeight / possibleWeight) * 100) : 0,
0387    }
0388  }
0389
0390  export function getCounterfactualScore(items: Requirement[], requirementId: string) {
