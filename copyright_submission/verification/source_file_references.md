# Source file references

| Area / claim | Source files and symbols |
|---|---|
| File constraints, supported MIME types, size limit, and PDF/ZIP signature checks. | `lib/resume-extraction.ts` lines 1–35; excerpt `01_resume_validation.ts` |
| PDF.js and Mammoth extraction, normalization, readable-text threshold, and parser cleanup. | `lib/resume-extraction.ts` lines 37–65; excerpt `02_resume_text_extraction.ts` |
| Versioned canonical IDs, explicit aliases, NFKC normalization, and complete-term matching boundaries. | `lib/analysis.ts` lines 49–108; excerpt `03_alias_taxonomy_and_normalization.ts` |
| Recognized requirements are extracted from lines; unsupported bullet requirements are retained with stable unmapped IDs. | `lib/analysis.ts` lines 238–280; excerpt `04_requirement_extraction.ts` |
| Evidence is classified as uncertain, missing, partial, or matched; matching includes cited text and section. | `lib/analysis.ts` lines 283–322; excerpt `05_evidence_classification.ts` |
| Weighted state credits and score breakdown computation. | `lib/analysis.ts` lines 333–372; excerpt `06_weighted_score_and_counterfactual.ts` |
| Heuristic proficiency levels depend on number and type of contextual evidence, with explicit limitations. | `lib/analysis.ts` lines 177–208; excerpt `07_proficiency_estimate.ts` |
| Counterfactual score replaces one requirement state with matched; recommendation text describes hypothetical score. | `lib/analysis.ts` lines 377–390; excerpt `08_hypothetical_recommendation.ts` |
| Authenticated upload, validation, extraction, owner-prefixed private object path, and database persistence. | `app/api/resumes/route.ts` lines 29–80; excerpt `09_upload_ownership_and_storage.ts` |
| Authenticated ownership check, deterministic analysis, JSON result persistence, transaction and scoped cleanup. | `app/api/analyses/route.ts` lines 24–73; excerpt `10_analysis_transaction.ts` |
| Token baseline, limited section/order/verb transformations, and experiment execution. | `lib/research.ts` lines 14–55; excerpt `11_research_transformations.ts` |
| Forecast route reads a generated readiness artifact and returns unavailable on absent/insufficient status. | `lib/forecast/readiness.ts` lines 1–30; excerpt `12_forecast_readiness_gate.ts` |
| Authenticated identity | `lib/auth.ts`: `getAuthenticatedUser`; `lib/supabase/server.ts` |
| Database TLS | `lib/db.ts`: Pool `rejectUnauthorized: true` |
| Database schema / row ownership | `supabase/schema.sql`: tables, RLS, private bucket policies |
| Browser analysis dashboard | `app/page.tsx`; `components/research-workspace.tsx` |
| Future skills validation and provenance | `ml/skill-intelligence/future_skills/annotation.py`, `schemas.py`, `workflow.py`, `train.py` |
| Forecasting readiness and unavailable response | `lib/forecast/readiness.ts`; `app/api/forecast/overview/route.ts`; `components/future-skill-forecast.tsx` |
| Collection quality | `ml/skill-intelligence/data/job-postings/reports/collection_quality.json`; `forecasting` report artifacts |
