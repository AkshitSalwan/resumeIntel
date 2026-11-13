# Screenshot index

All images are screenshots of the actual local ResumeIntel application. Captured from the production-mode local server using blank dummy configuration and without database access or user data.

| Figure | File | Route | Caption / evidence |
|---|---|---|---|
| 1 | `01_sign_in.png` | `/auth/signin` | Sign-in interface; empty credential fields. |
| 2 | `02_create_account.png` | `/auth/signup` | Account creation interface; no account data. |

No authenticated dashboard, resume upload, analysis result, evidence-detail, or future-skills interface is claimed as captured. To capture those: use a dedicated non-production Supabase/database and synthetic resume/job data; visit `/` after sign-in; use New analysis; inspect the saved report. `/dashboard/forecast` is authenticated but its displayed forecast content is unavailable; capture only to demonstrate that state. Avoid production `.env.local`, personal resumes, and real job applicant data.
