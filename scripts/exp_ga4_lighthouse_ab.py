#!/usr/bin/env python3
"""Lighthouse A/B: lazy GA4 (local) vs baseline simulado (gtag bloqueado no início)."""
import json
import statistics
import subprocess
import tempfile
from pathlib import Path

URL = "http://127.0.0.1:8012/"
RUNS = 3
OUT = Path("/tmp/lh_ga4_ab")


def lh_run(label, run_idx, block_gtag=False):
    out_dir = OUT / label / f"run_{run_idx}"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "report.json"

    cmd = [
        "npx",
        "--yes",
        "lighthouse",
        URL,
        "--quiet",
        "--chrome-flags=--headless --no-sandbox --disable-gpu",
        "--only-categories=performance",
        "--form-factor=mobile",
        "--screenEmulation.mobile",
        "--screenEmulation.width=390",
        "--screenEmulation.height=844",
        "--throttling-method=simulate",
        f"--output=json",
        f"--output-path={json_path}",
    ]

    env = None
    if block_gtag:
        # Baseline aproximado: bloquear download gtag via blocked-url-patterns (LH 12+)
        cmd.insert(1, "--blocked-url-patterns=*googletagmanager.com/gtag/js*")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(json_path.read_text())
    audits = data["audits"]
    metrics = {
        "performance": data["categories"]["performance"]["score"] * 100,
        "fcp_ms": audits["first-contentful-paint"]["numericValue"],
        "lcp_ms": audits["largest-contentful-paint"]["numericValue"],
        "tbt_ms": audits["total-blocking-time"]["numericValue"],
        "cls": audits["cumulative-layout-shift"]["numericValue"],
        "si_ms": audits["speed-index"]["numericValue"],
        "tti_ms": audits["interactive"]["numericValue"],
    }
    return metrics


def median(values):
    return statistics.median(values) if values else None


def summarize(label, rows):
    keys = ["performance", "fcp_ms", "lcp_ms", "tbt_ms", "cls", "si_ms", "tti_ms"]
    return {k: median([r[k] for r in rows]) for k in keys}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    lazy_rows = []
    baseline_rows = []

    for i in range(RUNS):
        lazy_rows.append(lh_run("lazy_local", i + 1, block_gtag=False))
        baseline_rows.append(lh_run("baseline_blocked_gtag", i + 1, block_gtag=True))

    report = {
        "lazy_local_median": summarize("lazy", lazy_rows),
        "baseline_blocked_gtag_median": summarize("baseline", baseline_rows),
        "lazy_runs": lazy_rows,
        "baseline_runs": baseline_rows,
    }
    print(json.dumps(report, indent=2))
    (OUT / "summary.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
