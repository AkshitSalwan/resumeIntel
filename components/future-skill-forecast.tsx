'use client'

import { useEffect, useState } from 'react'
import { Activity, ArrowRight, BarChart3, BriefcaseBusiness, CheckCircle2, ChevronDown, Clock3, Globe2, Layers3, RefreshCw, Search, ShieldCheck, Sparkles, Target, TrendingUp } from 'lucide-react'
import { FORECAST_HORIZONS, type ForecastHorizon } from '@/lib/forecast/types'

const unavailableMessage = 'Forecast data will appear here when the forecasting engine is connected.'

function UnavailableState({ compact = false }: { compact?: boolean }) {
  return <div className={`forecast-empty ${compact ? 'compact' : ''}`}><Clock3 size={compact ? 17 : 22} /><div><strong>Forecasting engine unavailable</strong><p>{unavailableMessage}</p></div></div>
}

function Selector({ label, value, onChange, icon: Icon, options }: { label: string; value: string; onChange: (value: string) => void; icon: typeof BriefcaseBusiness; options: string[] }) {
  return <label className="forecast-selector"><span>{label}</span><div><Icon size={15} /><select value={value} onChange={(event) => onChange(event.target.value)}><option value="">All {label.toLowerCase()}s</option>{options.map((option) => <option key={option} value={option}>{option}</option>)}</select><ChevronDown size={14} /></div></label>
}

export function FutureSkillForecast() {
  const [horizon, setHorizon] = useState<ForecastHorizon>(3)
  const [role, setRole] = useState('')
  const [industry, setIndustry] = useState('')
  const [region, setRegion] = useState('')
  const [search, setSearch] = useState('')
  const [readiness, setReadiness] = useState<{ message: string; dated: number | null; total: number | null } | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    void fetch(`/api/forecast/overview?horizon=${horizon}`, { signal: controller.signal })
      .then(async (response) => {
        const body = await response.json() as { message?: string; readiness?: { records_with_reliable_publication_dates?: number; total_records?: number } }
        if (body.readiness) {
          setReadiness({
            message: body.message ?? unavailableMessage,
            dated: body.readiness.records_with_reliable_publication_dates ?? null,
            total: body.readiness.total_records ?? null,
          })
        }
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setReadiness(null)
      })
    return () => controller.abort()
  }, [horizon])

  return <div className="forecast-page">
    <section className="forecast-hero">
      <div><p className="eyebrow">FUTURE SKILL INTELLIGENCE</p><h1>Future Skill Intelligence</h1><p className="hero-sub">Understand how technical and professional skill demand may evolve across roles, industries, and markets.</p></div>
      <button className="outline-button" type="button" disabled title="Available after forecasting engine integration"><RefreshCw size={15} /> Refresh forecast</button>
    </section>

    <section className="forecast-controls" aria-label="Forecast filters">
      <div className="horizon-control"><span>Forecast horizon</span><div className="horizon-options">{FORECAST_HORIZONS.map((value) => <button key={value} type="button" className={horizon === value ? 'selected' : ''} onClick={() => setHorizon(value)}>{value} year{value === 1 ? '' : 's'}</button>)}</div></div>
      <Selector label="Job role" value={role} onChange={setRole} icon={BriefcaseBusiness} options={['Software Engineer', 'Data Engineer', 'Product Manager']} />
      <Selector label="Industry" value={industry} onChange={setIndustry} icon={Layers3} options={['Technology', 'Financial services', 'Healthcare']} />
      <Selector label="Geographic market" value={region} onChange={setRegion} icon={Globe2} options={['Global', 'North America', 'Europe', 'Asia Pacific']} />
    </section>

    <div className="forecast-notice"><ShieldCheck size={16} /><span>{readiness ? `${readiness.message} ${readiness.dated ?? 'No'} of ${readiness.total ?? 'the'} postings have reliable publication dates.` : 'Forecasts will be evidence-backed and will clearly disclose confidence and limitations when data is available.'}</span></div>

    <section className="forecast-metric-grid" aria-label="Forecast overview">
      {[
        ['Emerging skills', Sparkles, 'Skills gaining relevance', 'indigo'],
        ['High-growth skills', TrendingUp, 'Strongest projected growth', 'violet'],
        ['Industry adoption', Activity, 'Coverage across industries', 'amber'],
        ['Forecast confidence', Target, 'Model confidence score', 'green'],
      ].map(([label, Icon, description, tone]) => <div className="forecast-metric-card" key={label as string}><div className={`forecast-metric-icon ${tone as string}`}><Icon size={18} /></div><div><p>{label as string}</p><strong>—</strong><span>{description as string}</span></div></div>)}
    </section>

    <div className="forecast-two-column">
      <section className="forecast-panel forecast-chart-panel"><div className="forecast-section-heading"><div><h2>Skill demand trajectory</h2><p>Historical demand and future projections for the selected scope.</p></div><BarChart3 size={18} /></div><UnavailableState /></section>
      <section className="forecast-panel"><div className="forecast-section-heading"><div><h2>Your Future Skill Gap</h2><p>Connect your resume profile to future role requirements.</p></div><Target size={18} /></div><UnavailableState /></section>
    </div>

    <section className="forecast-panel forecast-explorer"><div className="forecast-section-heading"><div><h2>Emerging skills explorer</h2><p>Explore evidence-backed skill forecasts when the engine is available.</p></div><span className="forecast-count">0 skills</span></div><div className="forecast-search"><Search size={16} /><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search skills" aria-label="Search skills" /></div><UnavailableState compact /></section>

    <section className="forecast-panel forecast-details"><div className="forecast-section-heading"><div><h2>Skill details</h2><p>Select a skill to review its trajectory, evidence, and limitations.</p></div><ArrowRight size={17} /></div><div className="forecast-detail-placeholder"><CheckCircle2 size={19} /><span>Select a skill from the explorer to see its future detail view.</span></div></section>
  </div>
}
