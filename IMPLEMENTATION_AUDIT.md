# Implementation audit

## End-to-end audit map and plan

### Feature-to-implementation map

| Feature | UI surface | API/server implementation | Persistence | Current audit status |
|---|---|---|---|---|
| Authentication | `app/auth/signin/page.tsx`, `app/auth/signup/page.tsx`, `components/auth-form.tsx` | Supabase browser auth, `lib/auth.ts`, `proxy.ts`, sign-out route | Supabase Auth | **NOT RUN** live lifecycle; static auth checks PASS |
| Dashboard | `app/page.tsx` | `GET /api/analyses` | `analyses` table | **PARTIAL**; analysis cards use API data, but workspace identity/date are hardcoded |
| Resume upload | New analysis UI in `app/page.tsx` | `POST /api/resumes` | `resumes` table and private `resumes` bucket | **PARTIAL**; upload path is implemented, browser workflow NOT RUN |
| Resume management | No dedicated management UI | No resume GET/list/update/delete route | Schema supports resume rows and deletion relationships | **NOT IMPLEMENTED** beyond upload |
| Resume extraction | Upload workflow | `lib/resume-extraction.ts` using `pdfjs-dist` and `mammoth` | Extracted text stored in `resumes.extracted_text` | Unit coverage and live PDF/DOCX coverage are **NOT RUN** |
| ATS analysis | New analysis flow and saved report view in `app/page.tsx` | `POST/GET /api/analyses`, `GET /api/analyses/[id]` | `analyses.result` JSONB | Engine unit tests PASS; end-to-end persistence comparison **NOT RUN** |
| Research | `components/research-workspace.tsx` | `POST/GET /api/research` | `research_experiments`, `research_runs` | Engine tests PASS; live API and refresh/re-login persistence **NOT RUN** |
| Manuscripts | Manuscript editor in `components/research-workspace.tsx` | Revision insert branch in `POST /api/research` | `manuscript_sections`, `manuscript_revisions` | **FAIL** UI save is notice-only and does not create a section or revision |
| Security ownership | Dashboard/API server boundaries | `getAuthenticatedUser`, owner-scoped SQL, RLS/Storage policies | Supabase RLS and private Storage | Static checks PASS; non-production live audit previously PASS; production two-user test **NOT RUN** |
| TLS/database connectivity | Server-only `lib/db.ts` | `scripts/verify-db-connection.mjs` | PostgreSQL/Supabase | **PASS** previously verified with strict TLS |

### Incremental audit plan

1. Complete static inventory and identify implemented versus missing workflows.
2. Run unit, lint, build, and safe read-only database connectivity checks.
3. Execute browser authentication and feature workflows against a non-production environment.
4. Compare API responses, database records, Storage objects, and rendered results.
5. Run the existing two-user security integration only with isolated non-production credentials.
6. Add focused tests only for confirmed gaps, then rerun the validation suite.
7. Record PASS, FAIL, BLOCKED, NOT IMPLEMENTED, and NOT RUN separately for UI, API, database, and security evidence.

The browser and live integration phases remain separate from the automated checks below. No production data is used for destructive testing.

### Phase 1 and validation evidence

- **PASS:** `pnpm test` — 4 test files, 41 tests passed.
- **PASS:** `pnpm lint`.
- **PASS:** `pnpm build` — Next.js 16.4.4 production build completed and listed the expected App Router/API routes.
- **PASS:** `pnpm db:verify` — PostgreSQL `SELECT 1` succeeded with certificate validation enabled.
- **NOT RUN:** Browser authentication lifecycle; no browser test runner is configured and the available `.env.local` targets production.
- **NOT RUN:** Live PDF/DOCX upload, Storage object verification, analysis persistence comparison, research refresh/re-login, and manuscript browser flows.
- **NOT RUN:** Two-user live security workflow in this audit; the configured test-account variables must not be used against the production target.

Confirmed implementation findings and remediation status:

- **PASS:** Resume list, item retrieval, metadata update, and owner-checked deletion are implemented in `app/api/resumes` and `app/api/resumes/[id]`; the dashboard lists and deletes the authenticated user's resumes.
- **PASS:** Failed analysis compensation is scoped by authenticated owner, resume ID, and a server-generated workflow token. It cannot delete an older resume without the matching token.
- **PASS:** Research history and manuscript sections/revisions are loaded through authenticated endpoints on dashboard initialization.
- **PASS:** Manuscript creation and revision saving use `app/api/manuscripts`; revisions are append-only and ownership-scoped.
- **PASS:** Dashboard identity, initials, date, resume names, and research count are derived from authenticated/profile/persisted data.
- **BLOCKED:** Live browser and two-user verification remains unavailable until `.env.audit.local` is configured with an isolated non-production project.

### Functional remediation changes

- Added `supabase/phase2-functional-remediation.sql`. It adds the nullable `resumes.workflow_token` column and a partial index. This migration has not been applied to production.
- The application must run this additive migration in the intended environment before new upload-to-analysis compensation is used.
- Existing rows and existing demo-user data are preserved; the migration does not reassign, delete, or overwrite data.

These findings are based on source inspection; live browser behavior remains **NOT RUN** until an isolated non-production environment is configured.

### Isolated audit environment

- **FAIL/BLOCKED:** `.env.audit.local` does not exist, so no non-production credentials were available for this audit.
- **PASS:** `.env.audit.local` is covered by `.gitignore`.
- **PASS:** `scripts/supabase-rls-storage-audit.mjs` now loads only `.env.audit.local`, checks owner-only file permissions, rejects a production project URL, and never falls back to `.env.local` or inherited environment variables.
- **PASS:** The script was executed without the file and failed closed with exit code `2`; no Supabase request was made.
- **NOT RUN:** User A authentication, User B authentication, database isolation, Storage isolation, and browser workflows.

### Non-production integration readiness update

- **PASS:** `.env.audit.local` exists and is now mode `600`.
- **PASS:** Required audit variable names are present without exposing their values.
- **FAIL:** The Supabase project configured in `.env.audit.local` is the same project as production. The audit script rejected it before authentication or any database/Storage write.
- **NOT RUN:** User A and User B authentication.
- **NOT RUN:** Functional migration application or verification.
- **NOT RUN:** Resume CRUD, failed-analysis cleanup, research persistence, manuscript persistence, refresh/re-login, or cleanup tests.

The functional migration remains additive and safe for existing rows:

- Adds nullable `resumes.workflow_token uuid`.
- Adds a partial index only for non-null workflow tokens.
- Does not alter existing values, RLS policies, Storage policies, or demo-user records.

The migration has **not** been applied to production or the incorrectly configured audit project.

## Initial Vercel deployment review

Validation completed for the current implementation:

- **PASS:** `pnpm test` — 4 files, 43 tests.
- **PASS:** `pnpm lint`.
- **PASS:** `pnpm build`.
- **PASS:** `git diff --check`.
- **PASS:** Exact production server values were absent from the generated client bundle.
- **PASS:** Production database hostname matches the configured Supabase project hostname.
- **PASS:** Production PostgreSQL TLS connection uses `rejectUnauthorized: true`.
- **PASS:** Production read-only catalog verification now reports `workflow_token`, `resumes_workflow_token_idx`, and resume RLS enabled. No migration was executed by this deployment review.

### Vercel environment variables

Required by the current application:

- **Browser-safe:** `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`.
- **Server/database:** `DATABASE_URL`.
- **Server/TLS:** exactly one of `SUPABASE_DB_CA_CERT` or `DATABASE_CA_CERT_PATH`.

`DATABASE_CA_CERT_PATH` currently points to a developer-machine path and is not suitable for Vercel. Configure the trusted PEM as the server-only `SUPABASE_DB_CA_CERT` Vercel environment variable instead; do not commit the certificate or use `rejectUnauthorized: false`.

`SUPABASE_SECRET_KEY` and `SUPABASE_JWKS_URL` are documented but are not consumed by the current application code. Do not add an unused privileged secret to Vercel unless a future server feature requires it.

The four `SUPABASE_TEST_USER_*` variables are test-only and must not be configured in Vercel production.

### Vercel configuration

No `vercel.json` or `.vercelignore` is present. Vercel can use the repository defaults:

- Install command: `pnpm install --frozen-lockfile`
- Build command: `pnpm build`
- Output: Next.js default
- Node runtime: use a version compatible with the lockfile/dependencies (pin the Vercel project to the tested Node version)

### Migration history and deployment blocker

The repository has one tracked baseline SQL file, `supabase/schema.sql`; `phase1-audit.sql` and `phase2-functional-remediation.sql` are additive SQL files but are not tracked migration-history entries. The current code requires:

1. `schema.sql`
2. `phase1-audit.sql`
3. `phase2-functional-remediation.sql`

The live production catalog currently confirms the workflow-token column and partial index exist, so the functional migration appears applied. This review did not apply any SQL. Confirm the same objects in the intended Vercel-linked Supabase project immediately before deployment.

Deploying the current code without `workflow_token` would cause `POST /api/resumes` to fail when inserting the new column and would prevent the failed-analysis compensating cleanup from safely identifying the workflow-created resume. Do not deploy before confirming the column exists.

## Research modules

### Research workspace UX polish

- **PASS:** The existing Research workspace now provides explicit method guidance, input character counts, readiness feedback, disabled invalid actions, clear pending/complete states, accessible live output, and a manuscript save footer without changing API or persistence behavior.
- **PASS:** `pnpm test`, `pnpm lint`, `pnpm build`, and `git diff --check` passed after the UI changes.
- **NOT RUN:** Browser visual regression testing; no browser test framework is configured.

- **Verified:** `lib/analysis.ts` remains the deterministic, evidence-backed scoring engine.
- **Verified:** `lib/research.ts` executes keyword and proposed-method baselines, counterfactual/robustness transformations, score deltas, and qualification-preservation metrics.
- **Verified:** `POST /api/research` executes before persisting an experiment and its `research_runs` result. Failed execution is returned as an error and is not saved as a successful run.
- **Verified:** `GET /api/research` reads persisted runs and manuscript sections for the current workspace owner.
- **Verified:** the Research workspace labels an empty output as **Pending execution** and only displays metrics returned by an executed run.
- **Verified:** manuscript revisions are persisted through the research API when a section id and content are supplied.
- **Verified:** protected API routes derive ownership from the verified Supabase session user UUID; no active `demo-user` fallback remains.
- **Verified:** manuscript revision writes verify that the referenced section belongs to the authenticated user before inserting a revision.
- **Prepared:** `pnpm security:integration` runs an opt-in two-user live RLS and private-storage audit using dedicated non-production accounts; it cleans only resources created with its unique test prefix.
- **Pending:** browser upload-to-research handoff is not automatic; the research form currently accepts extracted text explicitly so no extraction is fabricated.

## Test coverage

`tests/research.test.ts` covers deterministic replay, robustness qualification preservation, keyword matching, and invalid empty-run rejection.

## Local authenticated smoke test

Executed against the locally running Next.js application using the manually authenticated browser session:

- **PASS:** `GET /` redirected an unauthenticated browser to `/auth/signin`.
- **PASS:** Unauthenticated `GET /api/analyses`, `/api/research`, `/api/resumes`, `/api/manuscripts`, and `/api/me` returned `401`.
- **PASS:** Invalid sign-in credentials displayed a safe error without exposing authentication details.
- **PASS:** Authenticated dashboard loaded the current user identity and persisted empty-state counts.
- **PASS:** A real PDF resume upload completed with `POST /api/resumes` returning `201`.
- **PASS:** The upload created a persisted resume visible in the dashboard with filename, MIME type, size, and timestamp.
- **PASS:** A real analysis request completed with `POST /api/analyses` returning `201`.
- **PASS:** The persisted analysis was returned by `GET /api/analyses` and rendered in the dashboard with score, status, and evidence gaps.
- **PASS:** Browser refresh reloaded the authenticated session and restored the persisted resume and analysis after the initial API requests completed.
- **PASS:** Authenticated `GET /api/research` and `GET /api/manuscripts` returned `200`.
- **PASS:** Invalid authenticated requests to research, manuscripts, analyses, and resume upload returned `400` without creating records.
- **NOT RUN:** DOCX upload, Storage object inspection, cross-user access, sign-out click-through, research creation, and manuscript creation were not executed against the current configured production target to avoid adding or deleting more production data.
- **RESOLVED:** The prior browser hydration mismatch was caused by locale-sensitive `Intl.DateTimeFormat` in `app/page.tsx`, where the server rendered `TUESDAY, NOVEMBER 3, 2026` and the browser rendered `TUESDAY, 3 NOVEMBER 2026`.
- **PASS:** The dashboard date now uses an explicit `en-GB` locale and `UTC` timezone through `lib/date-format.ts`, preventing browser-locale differences and local-midnight server/browser disagreement. Regression coverage is in `tests/date-format.test.ts`.
- **NOT RUN:** Automated browser test suite; no Playwright or Cypress suite is configured.

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

The saved report is retrieved through `GET /api/analyses/:id`. Protected routes derive ownership from the verified Supabase session user UUID. The PostgreSQL pool and Supabase secret key remain server-only.

## Phase 3 security boundary

Apply [`supabase/schema.sql`](./supabase/schema.sql) to enable owner-based RLS policies and create the private `resumes` Storage bucket. Existing `demo-user` rows are not reassigned automatically. New resume uploads store the original file under `<authenticated-user-uuid>/<random-id>-<filename>` and remove the Storage object if the database insert fails.

The browser may use only `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`. `DATABASE_URL` and `SUPABASE_SECRET_KEY` must never use a `NEXT_PUBLIC_` prefix or be imported by client modules.

## PostgreSQL TLS verification

The PostgreSQL client requires certificate validation with `rejectUnauthorized: true` and supports the trusted Supabase CA through the server-only `SUPABASE_DB_CA_CERT` or `DATABASE_CA_CERT_PATH` variable. Supabase's official SSL guidance identifies the Dashboard's Database Settings > SSL Configuration download as the authoritative CA source. The installed production CA is the Supabase Root 2021 CA with SHA-256 fingerprint `80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA`. It matches the root presented by the configured production endpoint, and `pnpm db:verify` successfully executed a database query with strict certificate validation enabled. An invalid CA was rejected with `self-signed certificate in certificate chain`; no TLS bypass is configured.

## Phase 3 RLS and storage verification

Live verification requires dedicated non-production accounts supplied through environment variables:

- `SUPABASE_TEST_USER_A_EMAIL`
- `SUPABASE_TEST_USER_A_PASSWORD`
- `SUPABASE_TEST_USER_B_EMAIL`
- `SUPABASE_TEST_USER_B_PASSWORD`

Run `pnpm security:integration` only against an isolated non-production Supabase project. The script uses the publishable key, does not use the privileged secret key, does not reassign existing records, and does not delete resources outside its unique test data.

## Production Supabase verification

Read-only verification was performed against the configured production Supabase PostgreSQL endpoint using `DATABASE_CA_CERT_PATH` and `rejectUnauthorized: true`. The database hostname matched the configured Supabase project URL; credentials and connection values were not logged.

Status:

- **PASS:** `profiles`, `resumes`, `analyses`, `research_experiments`, `research_runs`, `manuscript_sections`, and `manuscript_revisions` exist.
- **PASS:** RLS is enabled on all seven public user-owned tables.
- **PASS:** 28 public-table policies exist: four authenticated owner policies per table, with `auth.uid()` ownership checks. Cross-table insert policies also verify the referenced resume, research experiment, or manuscript section owner.
- **PASS:** Four Storage policies exist for `resumes` objects. SELECT, INSERT, UPDATE, and DELETE are restricted to `bucket_id = 'resumes'` and the first object path segment matching `auth.uid()`.
- **PASS:** The `resumes` Storage bucket exists and `public = false`.
- **PASS:** No server-only credential names or values were found in `.next/static`.
- **FAIL:** The local production environment file contains one or more `SUPABASE_TEST_USER_*` variable names. Remove all test-account variables from the production deployment environment; test credentials must remain limited to isolated non-production environments.

No schema SQL was executed during this verification, and no production data was modified.
