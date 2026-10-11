# Implementation audit

## Research modules

- **Verified:** `lib/analysis.ts` remains the deterministic, evidence-backed scoring engine.
- **Verified:** `lib/research.ts` executes keyword and proposed-method baselines, counterfactual/robustness transformations, score deltas, and qualification-preservation metrics.
- **Verified:** `POST /api/research` executes before persisting an experiment and its `research_runs` result. Failed execution is returned as an error and is not saved as a successful run.
- **Verified:** `GET /api/research` reads persisted runs and manuscript sections for the current workspace owner.
- **Verified:** the Research workspace labels an empty output as **Pending execution** and only displays metrics returned by an executed run.
- **Verified:** manuscript revisions are persisted through the research API when a section id and content are supplied.
- **Pending:** authentication is not yet connected; the current workspace uses the existing demo owner id and must be replaced with a verified session owner before multi-user release.
- **Pending:** browser upload-to-research handoff is not automatic; the research form currently accepts extracted text explicitly so no extraction is fabricated.

## Test coverage

`tests/research.test.ts` covers deterministic replay, robustness qualification preservation, keyword matching, and invalid empty-run rejection.

## Supabase setup

Run [`supabase/schema.sql`](./supabase/schema.sql) once in the Supabase SQL Editor before using the API routes. The application expects the tables defined there, including `resumes`, `analyses`, research tables, and manuscript tables.

## Phase 2 deterministic analysis

The core workflow stores the complete reproducible analysis result in `analyses.result` as JSONB. The result includes the taxonomy version, stable requirement IDs, requirement text, normalized names, categories, evidence excerpts, resume sections, source locations, matching methods, explanations, per-requirement score contributions, score breakdown, and score definition. Existing reports remain readable because the JSONB result is extended without changing the `analyses` table relationship.

The compatibility estimate is calculated as:

`round(sum(requirement weight * status multiplier) / sum(requirement weight) * 100)`

Required requirements have weight `5`; preferred requirements have weight `3`. Status multipliers are:

- `matched`: `1.0`
- `partial`: `0.55`
- `uncertain`: `0.35`
- `missing`: `0`

This is an internal deterministic job-description match score, not an employer ATS score or hiring prediction. Skill aliases are maintained separately from scoring and normalized into one taxonomy requirement so aliases such as `React`, `React.js`, and `ReactJS` are not double-counted. Complete-term matching avoids arbitrary substrings and keeps ambiguous short aliases such as `JS` from matching inside `React.js`. A term found only in a skills list is classified as `partial` rather than demonstrated experience. Project evidence is labeled as project exposure, not employment experience, and missing evidence is reported explicitly.

## Phase 5 proficiency estimation

Analysis results also include optional `proficiencies` and `proficiencyDefinition` fields. The estimator is separate from the ATS match score and uses only deterministic, source-grounded evidence:

- `NOT_ENOUGH_EVIDENCE`: no usable contextual evidence, including an explicitly negative statement.
- `FOUNDATIONAL`: skills-list, education, certification, or basic exposure evidence.
- `INTERMEDIATE`: one detailed contextual implementation or responsibility example.
- `ADVANCED`: at least two distinct detailed implementation or responsibility examples.

Repeated identical excerpts are deduplicated. Each estimate stores the canonical skill name, level, evidence-strength label (`LOW`, `MEDIUM`, or `HIGH`), source excerpts, resume sections, signal type, explanation, and uncertainty note. Confidence is not statistically calibrated. Existing JSONB reports without proficiency fields remain readable.

The saved report is retrieved through `GET /api/analyses/:id`. Protected routes now derive ownership from the verified Supabase session user UUID. The PostgreSQL pool and Supabase secret key remain server-only.

## Phase 3 security boundary

Apply [`supabase/schema.sql`](./supabase/schema.sql) to enable owner-based RLS policies and create the private `resumes` Storage bucket. Existing `demo-user` rows are not reassigned automatically. New resume uploads store the original file under `<authenticated-user-uuid>/<random-id>-<filename>` and remove the Storage object if the database insert fails.

The browser may use only `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. `DATABASE_URL` and `SUPABASE_SECRET_KEY` must never use a `NEXT_PUBLIC_` prefix or be imported by client modules.
