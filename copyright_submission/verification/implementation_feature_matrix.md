# Implementation feature matrix

| Claim | Status | Evidence | Boundary / limitation |
|---|---|---|---|
| PDF/DOCX resume parsing | Implemented | `lib/resume-extraction.ts`; `app/api/resumes/route.ts` | Selectable text required; 10 MB cap; no OCR pipeline found. |
| Authenticated resume storage | Implemented | `lib/auth.ts`; `lib/supabase/server.ts`; `supabase/schema.sql` | Code-level inspection; no independent penetration test. |
| Requirement-level skill matching | Implemented | `lib/analysis.ts`: `extractRequirements`, `classifyEvidence` | Narrow 12-ID taxonomy and explicit aliases. |
| Explainable evidence and uncertainty | Implemented | `classifyEvidence`, `analyzeResume` | Deterministic excerpts; not semantic proof of skill. |
| Weighted score | Implemented | `calculateScoreBreakdown`, `SCORE_WEIGHTS` | Coverage index, not ATS score or hiring probability. |
| Proficiency estimate | Implemented, heuristic | `estimateSkillProficiencies` | Uncalibrated; does not verify competence. |
| Counterfactual score | Implemented | `getCounterfactualScore`, `getRecommendations` | Arithmetic what-if only. |
| Robustness experiments | Implemented, rudimentary | `lib/research.ts`: `transformResume`, `runExperiment` | Section removal/reversal and verb substitution do not prove semantic robustness. |
| Forecasting / future skills | Experimental, unavailable | `forecasting/`; `ml/skill-intelligence/`; `lib/forecast/readiness.ts`; API 503 | UI/API unavailable; sparse temporal data; no validated accuracy claim. |
| QLoRA fine-tuning | Experimental, gate blocked | `ml/skill-intelligence/future_skills/train.py`, `workflow.py`, gate/report | 56 train, 5 reviewed validation, 29 held-out gold; min validation 10; no adapter. |
| Tests/build at audit | Verified in this run | `pnpm test`, Python pytest, `pnpm lint`, Webpack build | Test status is point-in-time, not guarantee. |
