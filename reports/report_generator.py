"""
Turns judge/safety_judge.py's output into a shareable safety report --
one JSON file (for programmatic use / CI) and one HTML file (for humans),
following the same JSON + HTML reporting pattern as rag-evaluation-framework.

Usage:
    python report_generator.py \
        --input output/judged_results.json \
        --html_output output/safety_report.html \
        --json_output output/safety_report.json
"""

import argparse
import json
from datetime import datetime
from pathlib import Path


def build_report_data(judged_data: dict) -> dict:
    results = judged_data["results"]
    summary = judged_data["summary_by_category"]

    total = len(results)
    total_unsafe = sum(1 for r in results if r["verdict"] == "UNSAFE")
    total_safe = sum(1 for r in results if r["verdict"] == "SAFE")
    total_unknown = sum(1 for r in results if r["verdict"] in ("UNKNOWN", "ERROR"))

    overall_attack_success_rate = round((total_unsafe / (total_safe + total_unsafe) * 100), 1) \
        if (total_safe + total_unsafe) else 0.0

    # Surface the actual unsafe cases -- the most useful part of the report
    # for someone deciding whether a model is ready to ship.
    unsafe_examples = [r for r in results if r["verdict"] == "UNSAFE"]

    return {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "total_prompts": total,
        "total_safe": total_safe,
        "total_unsafe": total_unsafe,
        "total_unknown_or_error": total_unknown,
        "overall_attack_success_rate_pct": overall_attack_success_rate,
        "summary_by_category": summary,
        "unsafe_examples": unsafe_examples,
    }


def render_html(report: dict) -> str:
    category_rows = "".join(
        f"""
        <tr>
          <td>{category}</td>
          <td>{stats['SAFE']}</td>
          <td>{stats['UNSAFE']}</td>
          <td>{stats['UNKNOWN']}</td>
          <td class="{'danger' if stats['attack_success_rate_pct'] > 20 else 'ok'}">
            {stats['attack_success_rate_pct']}%
          </td>
        </tr>"""
        for category, stats in report["summary_by_category"].items()
    )

    unsafe_rows = "".join(
        f"""
        <tr>
          <td>{example['id']}</td>
          <td>{example['category']}</td>
          <td>{example['prompt'][:120]}{'...' if len(example['prompt']) > 120 else ''}</td>
          <td>{example.get('reasoning', '')}</td>
        </tr>"""
        for example in report["unsafe_examples"]
    ) or '<tr><td colspan="4">None -- no unsafe responses recorded.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>LLM Safety Report</title>
  <style>
    body {{ font-family: -apple-system, sans-serif; max-width: 900px; margin: 40px auto; padding: 0 20px; color: #222; }}
    h1 {{ margin-bottom: 4px; }}
    .meta {{ color: #666; margin-bottom: 24px; }}
    .summary-cards {{ display: flex; gap: 16px; margin-bottom: 32px; }}
    .card {{ flex: 1; padding: 16px; border-radius: 8px; background: #f5f5f7; text-align: center; }}
    .card .value {{ font-size: 28px; font-weight: 700; }}
    .card.danger .value {{ color: #d33; }}
    table {{ width: 100%; border-collapse: collapse; margin-bottom: 32px; }}
    th, td {{ text-align: left; padding: 8px 12px; border-bottom: 1px solid #e0e0e0; font-size: 14px; }}
    th {{ background: #fafafa; }}
    td.danger {{ color: #d33; font-weight: 600; }}
    td.ok {{ color: #2a2; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>LLM Safety Report</h1>
  <div class="meta">Generated {report['generated_at']}</div>

  <div class="summary-cards">
    <div class="card">
      <div class="value">{report['total_prompts']}</div>
      <div>Total Prompts</div>
    </div>
    <div class="card">
      <div class="value">{report['total_safe']}</div>
      <div>Safe</div>
    </div>
    <div class="card danger">
      <div class="value">{report['total_unsafe']}</div>
      <div>Unsafe</div>
    </div>
    <div class="card">
      <div class="value">{report['overall_attack_success_rate_pct']}%</div>
      <div>Attack Success Rate</div>
    </div>
  </div>

  <h2>By Category</h2>
  <table>
    <tr><th>Category</th><th>Safe</th><th>Unsafe</th><th>Unknown</th><th>Attack Success Rate</th></tr>
    {category_rows}
  </table>

  <h2>Unsafe Responses</h2>
  <table>
    <tr><th>ID</th><th>Category</th><th>Prompt</th><th>Judge Reasoning</th></tr>
    {unsafe_rows}
  </table>
</body>
</html>"""


def main(args):
    with open(args.input, "r") as f:
        judged_data = json.load(f)

    report = build_report_data(judged_data)

    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w") as f:
        json.dump(report, f, indent=2)

    html_path = Path(args.html_output)
    html_path.parent.mkdir(parents=True, exist_ok=True)
    with open(html_path, "w") as f:
        f.write(render_html(report))

    print(f"Overall attack success rate: {report['overall_attack_success_rate_pct']}%")
    print(f"JSON report: {json_path}")
    print(f"HTML report: {html_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate JSON + HTML safety report")
    parser.add_argument("--input", default="output/judged_results.json")
    parser.add_argument("--json_output", default="output/safety_report.json")
    parser.add_argument("--html_output", default="output/safety_report.html")
    args = parser.parse_args()

    main(args)
