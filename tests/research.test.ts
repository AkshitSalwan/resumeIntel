import { describe, expect, it } from 'vitest'
import { keywordBaseline, runExperiment, transformResume } from '../lib/research'

describe('research modules', () => {
  const resumeText = 'Python SQL PostgreSQL. Led a data pipeline and built dashboards.'
  const jobDescription = 'We need Python SQL and PostgreSQL experience building data pipelines.'

  it('produces a reproducible keyword baseline', () => {
    const first = runExperiment({ name: 'keywords', kind: 'baseline', baseline: 'keyword', resumeText, jobDescription })
    const second = runExperiment({ name: 'keywords', kind: 'baseline', baseline: 'keyword', resumeText, jobDescription })
    expect(first).toEqual(second)
    expect(first.executed).toBe(true)
    expect(first.metrics.score).toBe(first.score)
  })

  it('preserves qualification when reordering sections', () => {
    const transformed = transformResume(resumeText, 'reorder_sections')
    expect(transformed).not.toBe(resumeText)
    const result = runExperiment({ name: 'robustness', kind: 'robustness', transformation: 'reorder_sections', resumeText, jobDescription })
    expect(result.executed).toBe(true)
    expect(result.metrics.qualificationPreserved).toBe(1)
  })

  it('does not fabricate empty runs', () => {
    expect(() => runExperiment({ name: 'invalid', kind: 'counterfactual', resumeText: '', jobDescription })).toThrow()
    expect(keywordBaseline(resumeText, jobDescription).matched).toContain('python')
  })
})
