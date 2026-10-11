'use client'

import useSWR from 'swr'
import { useState } from 'react'
import { ResearchWorkspace } from '@/components/research-workspace'
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  Check,
  ChevronDown,
  CircleHelp,
  FileText,
  FlaskConical,
  LayoutDashboard,
  Menu,
  Plus,
  Search,
  Settings,
  ShieldCheck,
  Sparkles,
  Target,
  Upload,
  X,
} from 'lucide-react'

type StoredAnalysis = {
  id: string
  resume_id: string
  job_description: string
  result: {
    score: number
    scoreDefinition?: string
    proficiencyDefinition?: string
    proficiencies?: Array<{
      skill: string
      normalizedName: string
      level: 'NOT_ENOUGH_EVIDENCE' | 'FOUNDATIONAL' | 'INTERMEDIATE' | 'ADVANCED'
      confidence: 'LOW' | 'MEDIUM' | 'HIGH'
      explanation: string
      uncertainty: string
      evidence: Array<{ excerpt: string; section: string; sourceLocation: string; signal: string }>
    }>
    scoreBreakdown?: {
      required: { count: number; matched: number; partial: number; missing: number; uncertain: number; weightedScore: number; earnedWeight?: number; possibleWeight?: number }
      preferred: { count: number; matched: number; partial: number; missing: number; uncertain: number; weightedScore: number; earnedWeight?: number; possibleWeight?: number }
    }
    requirements: Array<{
      label: string
      requirementText?: string
      importance: 'required' | 'preferred'
      weight?: number
      status: 'matched' | 'partial' | 'missing' | 'uncertain'
      evidence?: string
      section?: string
      source?: string
      sourceLocation?: string
      explanation?: string
      scoreContribution?: { credit: number; earnedWeight: number; possibleWeight: number }
    }>
  }
  created_at: string
}

const fetcher = (url: string) => fetch(url).then(async (response) => {
  if (!response.ok) throw new Error('Could not load saved analyses')
  return response.json()
})

const nav = [
  { label: 'Overview', icon: LayoutDashboard },
  { label: 'New analysis', icon: Plus },
  { label: 'Robustness lab', icon: FlaskConical },
  { label: 'Research', icon: BarChart3 },
]

export default function Page() {
  const [active, setActive] = useState('Overview')
  const [showUpload, setShowUpload] = useState(false)
  const [fileName, setFileName] = useState('')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jobDescription, setJobDescription] = useState('')
  const [selectedAnalysis, setSelectedAnalysis] = useState<StoredAnalysis | null>(null)
  const [notice, setNotice] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [researchResume, setResearchResume] = useState('')
  const [researchJob, setResearchJob] = useState('')
  const [researchName, setResearchName] = useState('Counterfactual run')
  const [researchKind, setResearchKind] = useState<'counterfactual' | 'robustness' | 'baseline'>('counterfactual')
  const [researchOutput, setResearchOutput] = useState('')
  const [manuscript, setManuscript] = useState('')
  const [researchRunning, setResearchRunning] = useState(false)
  const { data: analysisData, error: analysisError, mutate: refreshAnalyses } = useSWR<{ analyses: StoredAnalysis[] }>('/api/analyses', fetcher)
  const analyses = analysisData?.analyses ?? []

  function notify(message: string) {
    setNotice(message)
    window.setTimeout(() => setNotice(''), 2800)
  }

  async function openAnalysis(id: string) {
    try {
      const response = await fetch(`/api/analyses/${id}`)
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Could not load the saved report')
      setSelectedAnalysis(data.analysis)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Could not load the saved report')
    }
  }

  async function runResearch() {
    if (!researchResume.trim() || !researchJob.trim()) { notify('Provide both resume text and job description'); return }
    setResearchRunning(true)
    try {
      const response = await fetch('/api/research', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name: researchName, kind: researchKind, resumeText: researchResume, jobDescription: researchJob, transformation: researchKind === 'baseline' ? undefined : 'reorder_sections', baseline: researchKind === 'baseline' ? 'keyword' : undefined }) })
      const data = await response.json()
      if (!response.ok) throw new Error(data.error || 'Research run failed')
      setResearchOutput(JSON.stringify(data.run.result, null, 2))
      notify('Executed and persisted research run')
    } catch (error) { notify(error instanceof Error ? error.message : 'Research run failed') } finally { setResearchRunning(false) }
  }

  async function saveManuscript() {
    if (!manuscript.trim()) { notify('Write a manuscript section first'); return }
    notify('Manuscript workspace is ready; create a section in the research database to save revisions')
  }

  async function submitAnalysis() {
    if (!resumeFile) {
      notify('Choose a PDF or DOCX resume first')
      return
    }
    if (jobDescription.trim().length < 80) {
      notify('Add a longer job description so the comparison is meaningful')
      return
    }

    setIsSubmitting(true)
    try {
      const uploadData = new FormData()
      uploadData.append('file', resumeFile)
      const uploadResponse = await fetch('/api/resumes', { method: 'POST', body: uploadData })
      const upload = await uploadResponse.json()
      if (!uploadResponse.ok) throw new Error(upload.error || 'Resume upload failed')

      const analysisResponse = await fetch('/api/analyses', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resumeId: upload.resume.id, jobDescription }),
      })
      const analysis = await analysisResponse.json()
      if (!analysisResponse.ok) throw new Error(analysis.error || 'Analysis failed')

      setShowUpload(false)
      setActive('Overview')
      setResumeFile(null)
      setFileName('')
      setJobDescription('')
      notify(`Analysis complete: ${analysis.analysis.result.score}% match`)
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Something went wrong. Try again.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><div className="brand-mark"><Sparkles size={16} /></div><span>resume<span className="brand-accent">intel</span></span></div>
        <div className="workspace"><div className="avatar">JD</div><div><p className="workspace-name">Jordan Davis</p><p className="workspace-sub">Personal workspace</p></div><ChevronDown size={14} /></div>
        <nav className="nav-list" aria-label="Main navigation">
          {nav.map(({ label, icon: Icon }) => <button key={label} className={`nav-item ${active === label ? 'active' : ''}`} onClick={() => { setActive(label); setShowUpload(false); if (label === 'Robustness lab' || label === 'Research') notify(`${label} workspace is ready for your next experiment`) }}><Icon size={17} /><span>{label}</span>{label === 'Research' && <span className="nav-badge">2</span>}</button>)}
        </nav>
        <div className="sidebar-bottom"><button className="nav-item"><Settings size={17} /><span>Settings</span></button><button className="nav-item"><CircleHelp size={17} /><span>Help center</span></button><div className="privacy-note"><ShieldCheck size={16} /><span>Your resume stays private</span></div></div>
      </aside>

      <main className="main-content">
        <header className="topbar"><button className="mobile-menu" aria-label="Open navigation"><Menu size={20} /></button><div className="breadcrumbs"><span>Workspace</span><span>/</span><strong>{active}</strong></div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={18} /></button><div className="top-avatar">JD</div></div></header>
        <div className="content-wrap">
          {active === 'Research' ? <ResearchWorkspace researchResume={researchResume} setResearchResume={setResearchResume} researchJob={researchJob} setResearchJob={setResearchJob} researchName={researchName} setResearchName={setResearchName} researchKind={researchKind} setResearchKind={setResearchKind} runResearch={runResearch} researchRunning={researchRunning} researchOutput={researchOutput} manuscript={manuscript} setManuscript={setManuscript} saveManuscript={saveManuscript} /> : active === 'New analysis' ? <NewAnalysisPage fileName={fileName} setFileName={setFileName} setResumeFile={setResumeFile} jobDescription={jobDescription} setJobDescription={setJobDescription} submitAnalysis={submitAnalysis} isSubmitting={isSubmitting} /> : active === 'Robustness lab' ? <RobustnessLab onRun={() => { setActive('Research'); setResearchKind('robustness'); notify('Robustness experiment ready to execute') }} /> : <>
          <section className="hero-row"><div><p className="eyebrow">MONDAY, OCTOBER 10, 2026</p><h1>Good morning, Jordan.</h1><p className="hero-sub">Turn your resume into your next opportunity.</p></div><button className="primary-button" onClick={() => { setActive('New analysis'); setShowUpload(false) }}><Plus size={17} /> New analysis</button></section>

          <section className="metric-grid" aria-label="Workspace summary">
            <div className="metric-card"><div className="metric-icon indigo"><Target size={18} /></div><div><p className="metric-label">Average match</p><p className="metric-value">{analyses.length ? Math.round(analyses.reduce((sum, item) => sum + item.result.score, 0) / analyses.length) : '—'}{analyses.length > 0 && <span>%</span>}</p><p className="metric-foot"><em>{analyses.length ? 'From saved analyses' : 'Pending first analysis'}</em></p></div></div>
            <div className="metric-card"><div className="metric-icon violet"><FileText size={18} /></div><div><p className="metric-label">Analyses completed</p><p className="metric-value">{analyses.length}</p><p className="metric-foot"><em>{analysisError ? 'Unable to load saved data' : 'Persisted in workspace'}</em></p></div></div>
            <div className="metric-card"><div className="metric-icon amber"><BookOpen size={18} /></div><div><p className="metric-label">Skills to strengthen</p><p className="metric-value">{analyses.reduce((sum, item) => sum + item.result.requirements.filter((requirement) => requirement.status !== 'matched').length, 0)}</p><p className="metric-foot"><em>Evidence gaps across saved analyses</em></p></div></div>
          </section>

          <section className="section-heading"><div><h2>Recent analyses</h2><p>Review your latest resume-to-role comparisons.</p></div><button className="text-button" onClick={() => notify('Showing all 12 analyses in your workspace')}>View all <ArrowRight size={15} /></button></section>
          <section className="analysis-card"><div className="table-head"><span>Analysis</span><span>Resume</span><span>Match</span><span>Status</span><span></span></div>{analyses.length ? analyses.map((analysis) => <AnalysisRow key={analysis.id} role="Saved job comparison" company="Persisted analysis" file={analysis.resume_id} score={String(analysis.result.score)} date={new Date(analysis.created_at).toLocaleDateString()} status="Complete" tone="success" onOpen={openAnalysis} id={analysis.id} />) : <div className="empty-state">{analysisError ? 'Saved analyses could not be loaded.' : 'No analyses yet. Run a real comparison to populate this workspace.'}</div>}</section>

          <div className="lower-grid"><section><div className="section-heading compact"><div><h2>Latest insight</h2><p>Derived from the most recent persisted result.</p></div></div><div className="insight-card">{analyses[0] ? <><div className="insight-top"><div className="insight-symbol"><Sparkles size={17} /></div><span className="tag">EVIDENCE-GROUNDED</span></div><h3>{analyses[0].result.requirements.find((requirement) => requirement.status !== 'matched')?.label ?? 'All detected requirements matched'}</h3><p>{analyses[0].result.requirements.find((requirement) => requirement.status !== 'matched')?.evidence ?? 'No evidence gaps were recorded in the latest executed analysis.'}</p></> : <><h3>No insight yet</h3><p>Run an analysis with an uploaded resume and job description to generate evidence-backed guidance.</p></>}</div></section><section><div className="section-heading compact"><div><h2>Skill coverage</h2><p>From persisted analysis evidence.</p></div></div><div className="skill-card">{analyses[0]?.result.requirements.length ? analyses[0].result.requirements.map((requirement) => <div className="skill-row" key={requirement.label}><div className={`skill-dot ${requirement.status === 'matched' ? 'success' : requirement.status === 'partial' ? 'warning' : 'danger'}`}></div><div className="skill-main"><strong>{requirement.label}</strong><span>{requirement.evidence ?? 'No matching resume evidence'}</span></div><span className={`status-pill ${requirement.status === 'matched' ? 'success' : requirement.status === 'partial' ? 'warning' : 'danger'}`}>{requirement.status}</span></div>) : <div className="empty-state">Pending a real analysis run.</div>}</div></section></div>
          {selectedAnalysis && <SavedReport analysis={selectedAnalysis} onClose={() => setSelectedAnalysis(null)} />}
          </>}
        </div>
      </main>

      {notice && <div className="toast" role="status">{notice}</div>}

      {showUpload && <div className="modal-backdrop" onClick={() => setShowUpload(false)}><div className="upload-modal" onClick={(e) => e.stopPropagation()}><button className="modal-close" onClick={() => setShowUpload(false)} aria-label="Close"><X size={18} /></button><div className="modal-icon"><Upload size={20} /></div><h2>Start a new analysis</h2><p>Compare your resume with a target role using transparent, evidence-grounded matching.</p><label className="upload-zone"><input type="file" accept=".pdf,.docx" onChange={(e) => { const file = e.target.files?.[0] || null; setResumeFile(file); setFileName(file?.name || '') }} />{fileName ? <><Check size={22} /><strong>{fileName}</strong><span>Ready to validate</span></> : <><Upload size={22} /><strong>Drop your resume here</strong><span>PDF or DOCX, up to 10 MB</span></>}</label><label className="field-label">Job description<textarea placeholder="Paste the job description you want to analyze..." rows={5} value={jobDescription} onChange={(e) => setJobDescription(e.target.value)}></textarea></label><button className="primary-button full" onClick={submitAnalysis} disabled={isSubmitting}>{isSubmitting ? 'Extracting and analyzing…' : 'Continue to validation'} {!isSubmitting && <ArrowRight size={16} />}</button><p className="modal-foot"><ShieldCheck size={14} /> Your files are processed securely and never used to train models.</p></div></div>}
    </div>
  )
}

function NewAnalysisPage({ fileName, setFileName, setResumeFile, jobDescription, setJobDescription, submitAnalysis, isSubmitting }: { fileName: string; setFileName: (value: string) => void; setResumeFile: (file: File | null) => void; jobDescription: string; setJobDescription: (value: string) => void; submitAnalysis: () => void; isSubmitting: boolean }) {
  return <section className="page-panel"><div className="page-intro"><div><p className="eyebrow">ANALYSIS INTAKE</p><h1>Build a grounded comparison</h1><p className="hero-sub">Upload a real resume and provide the target role. Extraction and scoring happen on the server.</p></div><span className="status-pill success">PDF / DOCX supported</span></div><div className="intake-layout"><div className="intake-step"><span className="step-number">1</span><div><h2>Upload your resume</h2><p>Validated before extraction. Nothing is scored from filenames or placeholders.</p><label className="upload-zone large"><input type="file" accept=".pdf,.docx" onChange={(e) => { const file = e.target.files?.[0] || null; setResumeFile(file); setFileName(file?.name || '') }} />{fileName ? <><Check size={24} /><strong>{fileName}</strong><span>Ready for server-side extraction</span></> : <><Upload size={24} /><strong>Choose a PDF or DOCX</strong><span>Maximum 10 MB</span></>}</label></div></div><div className="intake-step"><span className="step-number">2</span><div><h2>Paste the job description</h2><p>Requirements are classified with evidence from the extracted resume text.</p><textarea className="large-textarea" rows={12} value={jobDescription} onChange={(e) => setJobDescription(e.target.value)} placeholder="Paste the complete job description here..." /></div></div></div><div className="intake-footer"><span><ShieldCheck size={15} /> Private, deterministic, and explainable</span><button className="primary-button" onClick={submitAnalysis} disabled={isSubmitting}>{isSubmitting ? 'Extracting and analyzing…' : 'Run analysis'} <ArrowRight size={16} /></button></div></section>
}

function RobustnessLab({ onRun }: { onRun: () => void }) {
  return <section className="page-panel"><div className="page-intro"><div><p className="eyebrow">QUALIFICATION-PRESERVING TESTS</p><h1>Robustness lab</h1><p className="hero-sub">Test whether the deterministic score survives harmless presentation changes.</p></div><span className="status-pill warning">No run selected</span></div><div className="robustness-grid"><div className="lab-card featured"><div className="lab-icon"><FlaskConical size={20} /></div><h2>Reorder sections</h2><p>Move resume sections without changing their content. A stable engine should preserve qualifications and produce an auditable comparison.</p><div className="lab-meta"><span>Transformation</span><strong>reorder_sections</strong></div><button className="primary-button" onClick={onRun}>Configure experiment <ArrowRight size={16} /></button></div><div className="lab-card"><div className="lab-icon muted"><ShieldCheck size={20} /></div><h2>Pending runs</h2><p>No robustness result is shown here until you execute a run with real resume text and a job description.</p><span className="pending-label">PENDING EXECUTION</span></div></div><div className="audit-note"><ShieldCheck size={16} /><div><strong>What this lab guarantees</strong><span>Every displayed metric will reference an executed, persisted research run. Pending work remains explicitly labelled.</span></div></div></section>
}

function AnalysisRow({ role, company, file, score, date, status, tone, onOpen, id }: { role: string; company: string; file: string; score: string; date: string; status: string; tone: string; onOpen: (id: string) => void; id: string }) {
  return <div className="table-row"><div className="role-cell"><div className="company-mark">{company.slice(0, 1)}</div><div><strong>{role}</strong><span>{company}</span></div></div><div className="file-cell"><FileText size={15} /><span>{file}</span></div><div className="score-cell"><strong>{score}%</strong><div className="score-track"><i style={{ width: `${score}%` }} /></div></div><div><span className={`status-pill ${tone}`}>{status}</span><span className="date">{date}</span></div><button className="row-arrow" aria-label={`Open ${role}`} onClick={() => onOpen(id)}><ArrowRight size={16} /></button></div>
}

function SavedReport({ analysis, onClose }: { analysis: StoredAnalysis; onClose: () => void }) {
  const requirements = analysis.result.requirements
  const counts = {
    matched: requirements.filter((item) => item.status === 'matched').length,
    partial: requirements.filter((item) => item.status === 'partial').length,
    missing: requirements.filter((item) => item.status === 'missing').length,
  }
  return <section className="detail-banner" aria-live="polite"><div><strong>{analysis.result.score}% job-description match score</strong><span>Persisted report · {new Date(analysis.created_at).toLocaleString()}</span><p>{analysis.result.scoreDefinition ?? 'A deterministic score based on weighted resume evidence; it is not a hiring prediction.'}</p><p>{analysis.job_description}</p><div className="report-breakdown"><span>Matched: {counts.matched}</span><span>Partial: {counts.partial}</span><span>Missing: {counts.missing}</span>{analysis.result.scoreBreakdown && <><span>Required: {analysis.result.scoreBreakdown.required.weightedScore}%</span><span>Preferred: {analysis.result.scoreBreakdown.preferred.weightedScore}%</span></>}</div>{requirements.map((requirement) => <div className="report-requirement" key={`${requirement.importance}-${requirement.label}`}><div><strong>{requirement.label} · {requirement.importance}</strong><span className={`status-pill ${requirement.status === 'matched' ? 'success' : requirement.status === 'partial' ? 'warning' : 'danger'}`}>{requirement.status}</span></div><small>{requirement.requirementText ? `JD: ${requirement.requirementText}. ` : ''}{requirement.evidence ?? 'No supporting resume evidence was found.'}</small><small>{requirement.explanation ?? 'No explanation recorded.'}{requirement.section ? ` Section: ${requirement.section}.` : ''}{requirement.sourceLocation ? ` Location: ${requirement.sourceLocation}.` : ''}</small>{requirement.scoreContribution && <small>Score contribution: {requirement.scoreContribution.earnedWeight.toFixed(2)} / {requirement.scoreContribution.possibleWeight.toFixed(2)} weight ({requirement.scoreContribution.credit.toFixed(2)} credit).</small>}</div>)}{analysis.result.proficiencies?.length ? <div className="report-proficiencies"><h3>Evidence-based skill proficiency</h3><small>{analysis.result.proficiencyDefinition}</small>{analysis.result.proficiencies.map((proficiency) => <div className="report-requirement" key={proficiency.skill}><div><strong>{proficiency.normalizedName}</strong><span className={`status-pill ${proficiency.level === 'ADVANCED' ? 'success' : proficiency.level === 'INTERMEDIATE' ? 'warning' : 'danger'}`}>{proficiency.level}</span></div><small>Evidence strength: {proficiency.confidence}</small><small>{proficiency.explanation}</small>{proficiency.evidence.length ? proficiency.evidence.map((item) => <small key={`${item.section}-${item.excerpt}`}>“{item.excerpt}” · {item.section} · {item.signal}</small>) : <small>No supporting resume evidence was found. This does not establish that the skill is absent.</small>}<small>{proficiency.uncertainty}</small></div>)}</div> : null}</div><button className="outline-button" onClick={onClose}>Close <X size={14} /></button></section>
}
