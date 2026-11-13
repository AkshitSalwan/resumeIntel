# Future Skill Intelligence integration contract

The authenticated forecasting section is available at `/dashboard/forecast`. It intentionally renders unavailable states until a forecasting engine is integrated.

## API contract

All forecast endpoints require the existing Supabase-authenticated session:

- `GET /api/forecast/overview`
- `GET /api/forecast/skills`
- `GET /api/forecast/skills/:skillId`
- `GET /api/forecast/personalized`
- `POST /api/forecast/generate`

Overview and skills endpoints accept `role`, `industry`, `region`, and `horizon` (`1`, `3`, or `5`). Skills additionally accepts `category`, `search`, `page`, and `limit` (`1`–`100`). Invalid inputs return `400`; unauthenticated requests return `401` (or `503` when auth is not configured).

Until the engine is implemented, authenticated requests return `503` with:

```json
{
  "error": "forecast_unavailable",
  "message": "The forecasting engine has not been integrated yet. No forecast data is available.",
  "code": "FORECAST_ENGINE_NOT_INTEGRATED"
}
```

## Backend integration sequence

1. Implement a server-side forecasting service behind `lib/forecast/`; keep model and data-source credentials server-only.
2. Populate the `SkillForecast`, `ForecastOverview`, and `PersonalizedSkillGap` contracts in `lib/forecast/types.ts`.
3. Replace the unavailable responses with the service call after validating query parameters.
4. Scope personalized reads to the authenticated user and use the existing resume owner relationship; do not use service-role credentials to bypass RLS.
5. Add migrations only when the model's persistence requirements are known. Forecast output should remain unavailable rather than being synthesized when upstream data is missing.
6. Add fixture-backed route tests for response schemas, pagination, authorization, and user isolation before enabling the refresh action.

No forecasting tables or migrations are included in this foundation because the model, evidence schema, and retention requirements are not defined yet.
