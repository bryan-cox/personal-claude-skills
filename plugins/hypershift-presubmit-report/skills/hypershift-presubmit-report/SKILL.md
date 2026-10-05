---
name: hypershift-presubmit-report
description: Generate a pass/fail report for presubmit CI jobs on the openshift/hypershift repository. Use this skill whenever the user asks about HyperShift presubmit job health, CI pass rates, presubmit failures on hypershift, or wants a dashboard/report of how HyperShift CI is doing. Also trigger when the user mentions "presubmit report", "job health", "CI status for hypershift", or asks what's failing in HyperShift CI.
---

# HyperShift Presubmit Job Report

Generate a pass/fail report for presubmit CI jobs running against the `openshift/hypershift` repository on the `main` branch, sourced directly from the Prow API.

## What This Produces

A report (HTML or markdown) showing:
- Overall pass rate across all presubmit jobs
- Per-job breakdown with pass/fail/abort counts and visual pass-rate bars
- Recent failure details with PR numbers, authors, and links to Prow

## How to Use

Run the bundled Python script — it handles fetching from Prow, filtering, and rendering.

```bash
# Default: HTML report for the last 24 hours, printed to stdout
python3 <skill-path>/scripts/fetch_presubmit_report.py

# Save HTML report to a file and open it
python3 <skill-path>/scripts/fetch_presubmit_report.py -o /tmp/hypershift-presubmit-report.html
open /tmp/hypershift-presubmit-report.html

# Markdown format
python3 <skill-path>/scripts/fetch_presubmit_report.py --format markdown

# JSON format (for further processing)
python3 <skill-path>/scripts/fetch_presubmit_report.py --format json

# Custom time range
python3 <skill-path>/scripts/fetch_presubmit_report.py --hours 12
python3 <skill-path>/scripts/fetch_presubmit_report.py --since 2026-03-18T00:00:00Z --until 2026-03-19T00:00:00Z
```

Replace `<skill-path>` with the actual path to this skill's directory.

### Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--hours` | 24 | Number of hours to look back |
| `--since` | - | Start time in ISO 8601 format (overrides --hours) |
| `--until` | now | End time in ISO 8601 format |
| `--format` | html | Output format: `html`, `markdown`, or `json` |
| `-o` / `--output` | stdout | Write output to a file instead of stdout |

### Typical Workflow

1. Run the script with `--format html -o /tmp/hypershift-presubmit-report.html`
2. Open the file with `open /tmp/hypershift-presubmit-report.html`
3. Present the key findings to the user (overall pass rate, worst-performing jobs, notable failures)

If the user asks for markdown output, use `--format markdown` and display the output directly.

## Data Source & Limitations

- Data comes from the Prow Deck API at `prow.ci.openshift.org/prowjobs.js`
- No authentication required
- The API only retains **~24-48 hours** of recent jobs, so requests for longer time ranges may return incomplete data
- Pending and triggered jobs are excluded from the report (only completed jobs are counted)
- Only standard library Python is required (no pip install needed)

## Interpreting the Report

- **Pass Rate** = successes / total completed runs (excluding pending)
- Jobs are sorted worst-to-best so problem areas are immediately visible
- **Aborted** jobs are counted separately — these are usually cancelled by users or superseded by newer commits, not genuine failures
- The HTML report uses color coding: green (>=90%), yellow (>=70%), red (<70%)
