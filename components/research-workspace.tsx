'use client'

import type { Dispatch, SetStateAction } from 'react'
import { AlertCircle, BarChart3, BookOpen, CheckCircle2, FlaskConical, Play, Save } from 'lucide-react'

type Props = {
  researchResume: string; setResearchResume: Dispatch<SetStateAction<string>>
  researchJob: string; setResearchJob: Dispatch<SetStateAction<string>>
  researchName: string; setResearchName: Dispatch<SetStateAction<string>>
  researchKind: 'counterfactual' | 'robustness' | 'baseline'; setResearchKind: Dispatch<SetStateAction<'counterfactual' | 'robustness' | 'baseline'>>
  runResearch: () => void; researchRunning: boolean; researchOutput: string
  manuscript: string; setManuscript: Dispatch<SetStateAction<string>>; saveManuscript: () => void
}

export function ResearchWorkspace(props: Props) {
  const methodDescription = props.researchKind === 'counterfactual'
    ? 'Tests how a controlled change affects the qualification result.'
    : props.researchKind === 'robustness'
      ? 'Checks whether the qualification signal survives a transformation.'
      : 'Compares the deterministic result with a keyword-only baseline.'

  return <section className="research-workspace">
    <div className="hero-row"><div><p className="eyebrow">REPRODUCIBLE RESEARCH</p><h1>Research workspace</h1><p className="hero-sub">Run a saved experiment, review the evidence, and draft the next revision.</p></div><span className="status-pill success"><CheckCircle2 size={13} /> Engine verified</span></div>
    <div className="research-grid">
      <div className="research-card"><div className="research-card-heading"><span className="research-icon"><FlaskConical size={18} /></span><div><h2>Run an experiment</h2><p>Provide the two inputs used by the deterministic engine.</p></div></div>
        <div className="research-fields">
          <label className="field-label">Experiment name<input value={props.researchName} onChange={(e) => props.setResearchName(e.target.value)} placeholder="e.g. Skills baseline comparison" /></label>
          <label className="field-label">Method<select value={props.researchKind} onChange={(e) => props.setResearchKind(e.target.value as Props['researchKind'])}><option value="counterfactual">Counterfactual</option><option value="robustness">Qualification-preserving robustness</option><option value="baseline">Keyword baseline</option></select><span className="field-help">{methodDescription}</span></label>
          <label className="field-label">Resume text<textarea rows={7} value={props.researchResume} onChange={(e) => props.setResearchResume(e.target.value)} placeholder="Paste extracted resume text from an executed upload..." /><span className="field-meta">{props.researchResume.length.toLocaleString()} characters</span></label>
          <label className="field-label">Job description<textarea rows={7} value={props.researchJob} onChange={(e) => props.setResearchJob(e.target.value)} placeholder="Paste the target job description..." /><span className="field-meta">{props.researchJob.length.toLocaleString()} characters</span></label>
        </div>
        <div className="research-action"><span><span className={`input-status ${props.researchResume.trim() && props.researchJob.trim() ? 'ready' : ''}`} />{props.researchResume.trim() && props.researchJob.trim() ? 'Ready to execute' : 'Add both inputs to continue'}</span><button className="primary-button" onClick={props.runResearch} disabled={props.researchRunning || !props.researchResume.trim() || !props.researchJob.trim()}><Play size={16} /> {props.researchRunning ? 'Executing…' : 'Execute and persist run'}</button></div>
      </div>
      <div className="research-card output-card"><div className="research-card-heading"><span className="research-icon output"><BarChart3 size={18} /></span><div><h2>Run output</h2><p>{props.researchOutput ? 'Executed and persisted result' : 'Pending execution'}</p></div><span className={`status-pill ${props.researchOutput ? 'success' : 'warning'}`}>{props.researchOutput ? 'Complete' : 'Pending'}</span></div><pre className={`research-output ${props.researchOutput ? 'has-output' : ''}`} aria-live="polite">{props.researchOutput || 'Your result will appear here after the experiment completes.'}</pre>{!props.researchOutput && <div className="research-empty-hint"><AlertCircle size={14} /> No result is shown until an experiment has been executed.</div>}</div>
    </div>
    <div className="research-card manuscript-card"><div className="research-card-heading"><span className="research-icon manuscript"><BookOpen size={18} /></span><div><h2>Editable manuscript</h2><p>Draft methods, findings, and limitations. Each save preserves a revision.</p></div><span className="status-pill warning">Draft</span></div><textarea className="manuscript-editor" rows={10} value={props.manuscript} onChange={(e) => props.setManuscript(e.target.value)} placeholder="Write or paste a manuscript section here..." /><div className="manuscript-footer"><span>{props.manuscript.length.toLocaleString()} characters · revisions are append-only</span><button className="outline-button" onClick={props.saveManuscript} disabled={!props.manuscript.trim()}><Save size={15} /> Save revision</button></div></div>
  </section>
}
