#!/usr/bin/env python3
"""Lighthouse validation for document composite fix (local)."""
import json
import statistics
import subprocess
from pathlib import Path

URL = "http://127.0.0.1:8013/"
RUNS = 3
OUT = Path("/tmp/lh_composite_validation")


def lh_run(form_factor, width, height, run_idx):
    out_dir = OUT / form_factor / f"run_{run_idx}"
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
        f"--form-factor={form_factor}",
        f"--screenEmulation.width={width}",
        f"--screenEmulation.height={height}",
        "--throttling-method=simulate",
        "--output=json",
        f"--output-path={json_path}",
    ]
    if form_factor == "mobile":
        cmd.extend(["--screenEmulation.mobile"])
    else:
        cmd.append("--screenEmulation.disabled")

    subprocess.run(cmd, check=True, capture_output=True, text=True)
    data = json.loads(json_path.read_text())
    audits = data["audits"]
    return {
        "performance": data["categories"]["performance"]["score"] * 100,
        "fcp_ms": audits["first-contentful-paint"]["numericValue"],
        "lcp_ms": audits["largest-contentful-paint"]["numericValue"],
        "tbt_ms": audits["total-blocking-time"]["numericValue"],
        "cls": audits["cumulative-layout-shift"]["numericValue"],
        "si_ms": audits["speed-index"]["numericValue"],
    }


def median(rows, key):
    return statistics.median(r[key] for r in rows)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {}
    for label, ff, w, h in (
        ("mobile", "mobile", 390, 844),
        ("desktop", "desktop", 1440, 900),
    ):
        rows = [lh_run(ff, w, h, i + 1) for i in range(RUNS)]
        report[f"{label}_runs"] = rows
        report[f"{label}_median"] = {k: median(rows, k) for k in rows[0]}
    print(json.dumps(report, indent=2))
    (OUT / "summary.json").write_text(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
