from typing import Any


def forecasting_readiness(coverage: dict[str, Any], quality: dict[str, Any], role_counts: dict[str, int]) -> dict[str, Any]:
    dimensions = {
        "historical_time_coverage": "Sufficient for initial experimentation" if coverage.get("temporal_comparison_sufficient") else "Requires more data",
        "geographic_coverage": "Sufficient for initial experimentation" if coverage.get("geographic_regions", 0) >= 2 else "Insufficient evidence",
        "role_coverage": "Sufficient for initial experimentation" if len(role_counts) >= 2 else "Requires more data",
        "missing_data": "Sufficient for initial experimentation" if quality.get("missing_posting_dates", 0) == 0 else "Requires more data",
        "overall": "Not ready for forecasting" if coverage.get("status") != "available" or coverage.get("total_job_postings", 0) == 0 else "Requires further validation",
    }
    return {"dimensions": dimensions, "basis": "Rule-based readiness labels; no arbitrary confidence score is calculated."}
