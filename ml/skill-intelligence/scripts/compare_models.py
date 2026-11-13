from pathlib import Path

from _bootstrap import ROOT


def main() -> int:
    path = ROOT / "artifacts" / "evaluation" / "comparison_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("# Model comparison\n\nNo comparison was run because no gold evaluation set or trained adapter is available.\n", encoding="utf-8")
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
