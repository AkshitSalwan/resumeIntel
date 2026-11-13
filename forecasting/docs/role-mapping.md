# Job-role mapping

EDA role analysis uses the deterministic rules in
`forecasting/analytics/roles.py`. A normalized title is assigned only when
exactly one job family rule matches. Ambiguous or unknown titles are left
unassigned rather than forced into a family. The rules are a research
convenience for exploratory grouping, not a validated occupational taxonomy.
