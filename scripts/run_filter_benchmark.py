#!/usr/bin/env python3
"""Run unified filter benchmark over JSONL datasets.

Each JSONL line must contain a "messages" array with role/content pairs.
The last user message is used as test input.
"""

import argparse
import json
import os
import sys
from collections import Counter
from typing import Dict, List

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from filters.unified_filter import UnifiedFilter


def load_jsonl(path: str) -> List[Dict]:
    items = []
    with open(path, "r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def extract_user_text(entry: Dict) -> str:
    messages = entry.get("messages", [])
    for msg in reversed(messages):
        if msg.get("role") == "user":
            return msg.get("content", "")
    return ""


def run_benchmark(inputs: List[str]) -> Dict:
    filter_engine = UnifiedFilter()
    file_reports = []
    pattern_counts = Counter()
    reason_counts = Counter()

    for path in inputs:
        records = load_jsonl(path)
        total = 0
        blocked = 0

        for entry in records:
            text = extract_user_text(entry)
            if not text:
                continue
            total += 1
            result = filter_engine.apply(text)
            if result.blocked:
                blocked += 1
                reason_counts.update(result.reasons)
                pattern_counts.update(result.matched_patterns)

        file_reports.append({
            "file": path,
            "total": total,
            "blocked": blocked,
            "passed": total - blocked,
            "block_rate": (blocked / total * 100) if total else 0.0,
        })

    summary = {
        "files": file_reports,
        "reasons": dict(reason_counts.most_common()),
        "patterns": dict(pattern_counts.most_common(30)),
        "stats": filter_engine.stats(),
    }
    return summary


def write_report_md(report: Dict, output_path: str) -> None:
    lines = []
    lines.append("# Unified Filter Benchmark Report")
    lines.append("")
    stats = report.get("stats", {})
    lines.append("## Summary")
    lines.append(f"- Total checks: {int(stats.get('total_checks', 0))}")
    lines.append(f"- Blocked: {int(stats.get('blocked_count', 0))}")
    lines.append(f"- Block rate: {stats.get('block_rate', 0.0):.2f}%")
    lines.append("")

    lines.append("## Per File")
    for item in report.get("files", []):
        lines.append(
            f"- {os.path.basename(item['file'])}: total={item['total']} blocked={item['blocked']} "
            f"passed={item['passed']} block_rate={item['block_rate']:.2f}%"
        )
    lines.append("")

    lines.append("## Top Reasons")
    for reason, count in report.get("reasons", {}).items():
        lines.append(f"- {reason}: {count}")
    lines.append("")

    lines.append("## Top Patterns")
    for pattern, count in report.get("patterns", {}).items():
        lines.append(f"- {pattern}: {count}")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run unified filter benchmark")
    parser.add_argument("--inputs", nargs="+", required=True, help="Input JSONL files")
    parser.add_argument("--output-md", required=True, help="Markdown report output")
    parser.add_argument("--output-json", required=True, help="JSON report output")
    args = parser.parse_args()

    report = run_benchmark(args.inputs)

    os.makedirs(os.path.dirname(args.output_md), exist_ok=True)
    os.makedirs(os.path.dirname(args.output_json), exist_ok=True)

    write_report_md(report, args.output_md)
    with open(args.output_json, "w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)

    print("Report written:", args.output_md)


if __name__ == "__main__":
    main()
