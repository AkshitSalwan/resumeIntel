'use client'

import type { Dispatch, SetStateAction } from 'react'
import { BarChart3, BookOpen, FlaskConical, Play, Save } from 'lucide-react'

type Props = {
  researchResume: string; setResearchResume: Dispatch<SetStateAction<string>>
  researchJob: string; setResearchJob: Dispatch<SetStateAction<string>>
  researchName: string; setResearchName: Dispatch<SetStateAction<string>>
  researchKind: 'counterfactual' | 'robustness' | 'baseline'; setResearchKind: Dispatch<SetStateAction<'counterfactual' | 'robustness' | 'baseline'>>
  runResearch: () => void; researchRunning: boolean; researchOutput: string
  manuscript: string; setManuscript: Dispatch<SetStateAction<string>>; saveManuscript: () => void
}

export function ResearchWorkspace(props: Props) {
  return <section className="research-workspace">
    <div className="hero-row"><div><p className="eyebrow">REPRODUCIBLE RESEARCH</p><h1>Research workspace</h1><p className="hero-sub">Every metric below is executed, persisted, or clearly pending.</p></div><span className="status-pill success">Engine verified</span></div>
    <div className="research-grid">
      <div className="research-card"><div className="research-card-heading"><FlaskConical size={18} /><div><h2>Run an experiment</h2><p>Use the verified deterministic analysis engine.</p></div></div>
        <label className="field-label">Experiment name<input value={props.researchName} onChange={(e) => props.setResearchName(e.target.value)} /></label>
        <label className="field-label">Method<select value={props.researchKind} onChange={(e) => props.setResearchKind(e.target.value as Props['researchKind'])}><option value="counterfactual">Counterfactual</option><option value="robustness">Qualification-preserving robustness</option><option value="baseline">Keyword baseline</option></select></label>
        <label className="field-label">Resume text<textarea rows={7} value={props.researchResume} onChange={(e) => props.setResearchResume(e.target.value)} placeholder="Paste extracted resume text from an executed upload..." /></label>
        <label className="field-label">Job description<textarea rows={7} value={props.researchJob} onChange={(e) => props.setResearchJob(e.target.value)} placeholder="Paste the target job description..." /></label>
        <button className="primary-button" onClick={props.runResearch} disabled={props.researchRunning}><Play size={16} /> {props.researchRunning ? 'Executing…' : 'Execute and persist run'}</button>
      </div>
      <div className="research-card"><div className="research-card-heading"><BarChart3 size={18} /><div><h2>Run output</h2><p>{props.researchOutput ? 'Executed result' : 'Pending execution'}</p></div></div><pre className="research-output">{props.researchOutput || 'No result is shown until an experiment has been executed.'}</pre></div>
    </div>
    <div className="research-card manuscript-card"><div className="research-card-heading"><BookOpen size={18} /><div><h2>Editable manuscript</h2><p>Draft methods, findings, and limitations without presenting pending work as a result.</p></div></div><textarea className="manuscript-editor" rows={10} value={props.manuscript} onChange={(e) => props.setManuscript(e.target.value)} placeholder="Write or paste a manuscript section here..." /><button className="outline-button" onClick={props.saveManuscript}><Save size={15} /> Save revision</button></div>
  </section>
}
