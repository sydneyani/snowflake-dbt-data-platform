"""Render a reconciliation report as Markdown, JSON, and HTML."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from meridian.quality.reconcile import ReconciliationReport


def write_report(report: ReconciliationReport, directory: Path) -> dict[str, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths = {
        "markdown": directory / "reconciliation.md",
        "json": directory / "reconciliation.json",
        "html": directory / "reconciliation.html",
    }
    paths["markdown"].write_text(report.to_markdown(), encoding="utf-8")
    paths["json"].write_text(json.dumps(asdict(report), indent=2) + "\n", encoding="utf-8")
    paths["html"].write_text(_html(report), encoding="utf-8")
    return paths


def _html(report: ReconciliationReport) -> str:
    rows = []
    for check in report.checks:
        rows.append(
            "<tr>"
            f"<td>{_esc(check.name)}</td>"
            f"<td class='{check.status.lower()}'>{_esc(check.status)}</td>"
            f"<td>{_esc(check.source_value)}</td>"
            f"<td>{_esc(check.target_value)}</td>"
            f"<td>{_esc(check.variance)}</td>"
            f"<td>{_esc(check.detail)}</td>"
            "</tr>"
        )
    status = report.status
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"/>
<title>Meridian reconciliation {_esc(report.generated_at)}</title>
<style>
body {{ font-family: Georgia, serif; margin: 2rem auto; max-width: 1100px; color: #1c1917; }}
h1 {{ font-weight: 500; }}
.banner {{ padding: 0.8rem 1rem; border-radius: 6px; font-family: ui-sans-serif, sans-serif; }}
.pass {{ background: #ecfdf3; color: #166534; }}
.fail {{ background: #fef2f2; color: #991b1b; }}
.explained {{ background: #fffbeb; color: #92400e; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1.5rem; font-family: ui-sans-serif, sans-serif; font-size: 14px; }}
th, td {{ border-bottom: 1px solid #e7e5e4; text-align: left; padding: 0.55rem; vertical-align: top; }}
th {{ font-size: 12px; letter-spacing: 0.04em; text-transform: uppercase; color: #57534e; }}
</style>
</head>
<body>
<h1>Source-to-target reconciliation</h1>
<p class="banner {status.lower()}">Pipeline status {_esc(status)}. Seed {report.seed}. Generated {_esc(report.generated_at)}.</p>
<p>{_esc(report.summary)}</p>
<table>
<thead><tr><th>Check</th><th>Status</th><th>Source</th><th>Target</th><th>Variance</th><th>Detail</th></tr></thead>
<tbody>
{"".join(rows)}
</tbody>
</table>
</body>
</html>
"""


def _esc(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
