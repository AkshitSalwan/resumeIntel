from pathlib import Path

import pandas as pd


def generate_visualizations(
    coverage: dict,
    trends: pd.DataFrame,
    cooccurrence: pd.DataFrame,
    output_dir: str | Path,
) -> list[str]:
    """Write charts only when real rows are available."""
    if not coverage.get("total_job_postings"):
        return []
    import matplotlib.pyplot as plt

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    generated: list[str] = []
    yearly = pd.Series(coverage["postings_by_year"], dtype="int64")
    if not yearly.empty:
        ax = yearly.plot(kind="bar", title="Job postings by year")
        ax.set_xlabel("Year")
        ax.set_ylabel("Postings")
        path = destination / "postings_by_year.png"
        ax.figure.tight_layout()
        ax.figure.savefig(path, dpi=140)
        plt.close(ax.figure)
        generated.append(str(path))
    if not trends.empty:
        top = trends.groupby("skill_name", as_index=False)["demand_percentage"].mean().nlargest(15, "demand_percentage")
        ax = top.sort_values("demand_percentage").plot.barh(x="skill_name", y="demand_percentage", legend=False, title="Top skills by historical demand")
        ax.set_xlabel("Demand percentage")
        path = destination / "top_skills_by_demand.png"
        ax.figure.tight_layout()
        ax.figure.savefig(path, dpi=140)
        plt.close(ax.figure)
        generated.append(str(path))
    if not cooccurrence.empty:
        matrix = cooccurrence.pivot(index="skill_a_name", columns="skill_b_name", values="cooccurrence_count").fillna(0)
        figure, ax = plt.subplots()
        ax.imshow(matrix.to_numpy(), cmap="Blues", aspect="auto")
        ax.set_title("Skill co-occurrence counts")
        ax.set_xlabel("Skill B")
        ax.set_ylabel("Skill A")
        ax.set_xticks(range(len(matrix.columns)), matrix.columns, rotation=45, ha="right")
        ax.set_yticks(range(len(matrix.index)), matrix.index)
        path = destination / "skill_cooccurrence.png"
        figure.tight_layout()
        figure.savefig(path, dpi=140)
        plt.close(figure)
        generated.append(str(path))
    return generated
