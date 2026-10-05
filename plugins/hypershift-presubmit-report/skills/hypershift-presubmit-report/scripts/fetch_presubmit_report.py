#!/usr/bin/env python3
"""Fetch presubmit job pass/fail report for openshift/hypershift from Prow."""

import argparse
import json
import sys
import urllib.request
import urllib.error
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from html import escape

PROW_API = "https://prow.ci.openshift.org/prowjobs.js?omit=annotations,decoration_config,pod_spec"
PROW_BASE_URL = "https://prow.ci.openshift.org/view/gs/test-platform-results"
PROW_JOB_HISTORY_URL = "https://prow.ci.openshift.org/job-history/gs/test-platform-results/pr-logs/directory"


def fetch_prowjobs():
    """Fetch all recent prowjobs from the Prow API."""
    req = urllib.request.Request(PROW_API, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("items", [])
    except urllib.error.URLError as e:
        print(f"Error fetching Prow API: {e}", file=sys.stderr)
        sys.exit(1)


def filter_hypershift_presubmit(items, since, until):
    """Filter for openshift/hypershift presubmit jobs on main within time range."""
    filtered = []
    for item in items:
        spec = item.get("spec", {})
        refs = spec.get("refs", {})
        if (
            spec.get("type") != "presubmit"
            or refs.get("org") != "openshift"
            or refs.get("repo") != "hypershift"
            or refs.get("base_ref") != "main"
        ):
            continue

        ts_str = item.get("metadata", {}).get("creationTimestamp", "")
        if not ts_str:
            continue
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except ValueError:
            continue

        if ts < since or ts > until:
            continue

        state = item.get("status", {}).get("state", "unknown")
        # Skip pending/triggered jobs — they haven't completed yet
        if state in ("pending", "triggered"):
            continue

        job_name = spec.get("job", "unknown")
        pr_number = None
        pr_author = None
        pulls = refs.get("pulls", [])
        if pulls:
            pr_number = pulls[0].get("number")
            pr_author = pulls[0].get("author")

        prow_url = item.get("status", {}).get("url", "")

        filtered.append({
            "job_name": job_name,
            "state": state,
            "timestamp": ts.isoformat(),
            "pr_number": pr_number,
            "pr_author": pr_author,
            "prow_url": prow_url,
        })

    return filtered


def aggregate(jobs):
    """Aggregate pass/fail counts per job name."""
    agg = defaultdict(lambda: {"success": 0, "failure": 0, "aborted": 0, "error": 0, "total": 0})
    for job in jobs:
        name = job["job_name"]
        state = job["state"]
        agg[name]["total"] += 1
        if state == "success":
            agg[name]["success"] += 1
        elif state == "failure":
            agg[name]["failure"] += 1
        elif state == "aborted":
            agg[name]["aborted"] += 1
        else:
            agg[name]["error"] += 1
    return dict(agg)


def friendly_time_range(since, until):
    """Return a human-readable description of the time range like 'Past 24 hours'."""
    delta = until - since
    total_seconds = int(delta.total_seconds())
    if total_seconds <= 0:
        return "No time range"
    hours = total_seconds / 3600
    if hours < 1:
        minutes = total_seconds // 60
        return f"Past {minutes} minute{'s' if minutes != 1 else ''}"
    elif hours <= 48 and hours == int(hours):
        h = int(hours)
        return f"Past {h} hour{'s' if h != 1 else ''}"
    else:
        days = delta.days
        if days >= 1:
            return f"Past {days} day{'s' if days != 1 else ''}"
        return f"Past {hours:.1f} hours"


def render_markdown(agg, since, until, jobs):
    """Render the report as markdown."""
    lines = []
    friendly = friendly_time_range(since, until)
    lines.append(f"# HyperShift Presubmit Job Report")
    lines.append(f"")
    lines.append(f"**Repository:** openshift/hypershift (main branch)")
    lines.append(f"**Time Range:** {friendly}")
    lines.append(f"**Period:** {since.strftime('%Y-%m-%d %H:%M UTC')} to {until.strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append(f"**Total Runs:** {sum(v['total'] for v in agg.values())}")
    lines.append(f"")

    # Overall summary
    total_success = sum(v["success"] for v in agg.values())
    total_failure = sum(v["failure"] for v in agg.values())
    total_aborted = sum(v["aborted"] for v in agg.values())
    total_all = sum(v["total"] for v in agg.values())
    total_completed = total_success + total_failure
    overall_rate = (total_success / total_completed * 100) if total_completed > 0 else 0
    lines.append(f"## Overall Summary")
    lines.append(f"")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Pass Rate (excl. aborted) | {overall_rate:.1f}% |")
    lines.append(f"| Successes | {total_success} |")
    lines.append(f"| Failures | {total_failure} |")
    lines.append(f"| Aborted | {total_aborted} |")
    lines.append(f"| Total | {total_all} |")
    lines.append(f"")

    # Per-job table
    lines.append(f"## Per-Job Breakdown")
    lines.append(f"")
    lines.append(f"| Job | Pass Rate | Pass | Fail | Abort | Total |")
    lines.append(f"|-----|-----------|------|------|-------|-------|")

    sorted_jobs = sorted(agg.items(), key=lambda x: (x[1]["success"] / max(x[1]["success"] + x[1]["failure"], 1)))
    for name, counts in sorted_jobs:
        completed = counts["success"] + counts["failure"]
        rate = (counts["success"] / completed * 100) if completed > 0 else 100.0
        short_name = name.replace("pull-ci-openshift-hypershift-main-", "")
        lines.append(
            f"| {short_name} | {rate:.1f}% | {counts['success']} | {counts['failure']} | {counts['aborted']} | {counts['total']} |"
        )

    lines.append(f"")

    # Recent failures detail, grouped by job
    failures = [j for j in jobs if j["state"] == "failure"]
    if failures:
        lines.append(f"## Recent Failures")
        lines.append(f"")
        failures_by_job = defaultdict(list)
        for f in failures:
            short_name = f["job_name"].replace("pull-ci-openshift-hypershift-main-", "")
            failures_by_job[short_name].append(f)
        # Sort job groups by failure count descending
        for job_name, job_failures in sorted(failures_by_job.items(), key=lambda x: len(x[1]), reverse=True):
            full_job_name = job_failures[0]["job_name"]
            history_url = f"{PROW_JOB_HISTORY_URL}/{full_job_name}"
            lines.append(f"### [{job_name}]({history_url}) ({len(job_failures)} failures)")
            lines.append(f"")
            lines.append(f"| PR | Author | Time | Link |")
            lines.append(f"|----|--------|------|------|")
            for f in sorted(job_failures, key=lambda x: x["timestamp"], reverse=True):
                pr = f"#{f['pr_number']}" if f["pr_number"] else "N/A"
                author = f["pr_author"] or "N/A"
                time_str = f["timestamp"][:16].replace("T", " ")
                link = f"[Prow]({f['prow_url']})" if f["prow_url"] else "N/A"
                lines.append(f"| {pr} | {author} | {time_str} | {link} |")
            lines.append(f"")

    lines.append(f"")
    lines.append(f"---")
    lines.append(f"*Data from Prow API (limited to recent ~24-48h of jobs)*")
    return "\n".join(lines)


def render_html(agg, since, until, jobs):
    """Render the report as a standalone HTML file."""
    total_success = sum(v["success"] for v in agg.values())
    total_failure = sum(v["failure"] for v in agg.values())
    total_aborted = sum(v["aborted"] for v in agg.values())
    total_all = sum(v["total"] for v in agg.values())
    total_completed = total_success + total_failure
    overall_rate = (total_success / total_completed * 100) if total_completed > 0 else 0

    sorted_jobs = sorted(agg.items(), key=lambda x: (x[1]["success"] / max(x[1]["success"] + x[1]["failure"], 1)))
    failures = [j for j in jobs if j["state"] == "failure"]
    failures.sort(key=lambda x: x["timestamp"], reverse=True)

    def rate_color(rate):
        if rate >= 90:
            return "#22c55e"
        elif rate >= 70:
            return "#eab308"
        else:
            return "#ef4444"

    job_rows = ""
    for name, counts in sorted_jobs:
        completed = counts["success"] + counts["failure"]
        rate = (counts["success"] / completed * 100) if completed > 0 else 100.0
        short_name = escape(name.replace("pull-ci-openshift-hypershift-main-", ""))
        history_url = f"{PROW_JOB_HISTORY_URL}/{escape(name)}"
        color = rate_color(rate)
        bar_width = rate
        job_rows += f"""<tr>
  <td class="job-name"><a href="{history_url}" target="_blank">{short_name}</a></td>
  <td><div class="rate-bar"><div class="rate-fill" style="width:{bar_width}%;background:{color}"></div><span class="rate-text">{rate:.1f}%</span></div></td>
  <td class="num">{counts['success']}</td>
  <td class="num">{counts['failure']}</td>
  <td class="num">{counts['aborted']}</td>
  <td class="num">{counts['total']}</td>
</tr>"""

    # Group failures by job name
    failures_by_job = defaultdict(list)
    for f in failures:
        short_name = f["job_name"].replace("pull-ci-openshift-hypershift-main-", "")
        failures_by_job[short_name].append(f)
    # Sort job groups by failure count descending
    failure_sections = ""
    for job_name, job_failures in sorted(failures_by_job.items(), key=lambda x: len(x[1]), reverse=True):
        rows = ""
        for f in sorted(job_failures, key=lambda x: x["timestamp"], reverse=True):
            pr = f"#{f['pr_number']}" if f["pr_number"] else "N/A"
            author = escape(f["pr_author"] or "N/A")
            time_str = f["timestamp"][:16].replace("T", " ")
            link = f'<a href="{escape(f["prow_url"])}" target="_blank">View</a>' if f["prow_url"] else "N/A"
            rows += f"<tr><td>{pr}</td><td>{author}</td><td>{time_str}</td><td>{link}</td></tr>"
        full_job_name = job_failures[0]["job_name"]
        history_url = f"{PROW_JOB_HISTORY_URL}/{escape(full_job_name)}"
        failure_sections += f"""<h3><a href="{history_url}" target="_blank">{escape(job_name)}</a> <span style="color:#94a3b8;font-size:0.85rem">({len(job_failures)} failure{'s' if len(job_failures) != 1 else ''})</span></h3>
<table>
<thead><tr><th>PR</th><th>Author</th><th>Time</th><th>Link</th></tr></thead>
<tbody>{rows}</tbody>
</table>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>HyperShift Presubmit Report</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; }}
  h1 {{ font-size: 1.5rem; margin-bottom: 0.25rem; color: #f8fafc; }}
  .subtitle {{ color: #94a3b8; margin-bottom: 1.5rem; font-size: 0.9rem; }}
  .summary-cards {{ display: flex; gap: 1rem; margin-bottom: 2rem; flex-wrap: wrap; }}
  .card {{ background: #1e293b; border-radius: 8px; padding: 1rem 1.5rem; min-width: 140px; }}
  .card .label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.05em; }}
  .card .value {{ font-size: 1.75rem; font-weight: 700; margin-top: 0.25rem; }}
  .card .value.green {{ color: #22c55e; }}
  .card .value.red {{ color: #ef4444; }}
  .card .value.yellow {{ color: #eab308; }}
  .card .value.blue {{ color: #3b82f6; }}
  h2 {{ font-size: 1.1rem; margin: 1.5rem 0 0.75rem; color: #f8fafc; }}
  h3 {{ font-size: 0.95rem; margin: 1.25rem 0 0.5rem; color: #f1f5f9; }}
  table {{ width: 100%; border-collapse: collapse; background: #1e293b; border-radius: 8px; overflow: hidden; margin-bottom: 1.5rem; }}
  th {{ text-align: left; padding: 0.6rem 0.75rem; background: #334155; color: #94a3b8; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  td {{ padding: 0.5rem 0.75rem; border-top: 1px solid #334155; font-size: 0.85rem; }}
  .num {{ text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; width: 1%; }}
  .job-name {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 0.8rem; white-space: nowrap; width: 1%; }}
  .rate-bar {{ position: relative; background: #334155; border-radius: 4px; height: 22px; width: 100%; }}
  .rate-fill {{ height: 100%; border-radius: 4px; transition: width 0.3s; }}
  .rate-text {{ position: absolute; right: 6px; top: 2px; font-size: 0.75rem; font-weight: 600; color: #f8fafc; }}
  a {{ color: #60a5fa; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .footer {{ color: #64748b; font-size: 0.75rem; margin-top: 2rem; }}
  tr:hover {{ background: #253347; }}
</style>
</head>
<body>
<h1>HyperShift Presubmit Job Report</h1>
<div class="subtitle">openshift/hypershift &middot; main branch &middot; {escape(friendly_time_range(since, until))} &middot; {escape(since.strftime('%Y-%m-%d %H:%M UTC'))} to {escape(until.strftime('%Y-%m-%d %H:%M UTC'))}</div>

<div class="summary-cards">
  <div class="card"><div class="label">Pass Rate <span style="font-size:0.65rem;color:#64748b">(excl. aborted)</span></div><div class="value" style="color:{rate_color(overall_rate)}">{overall_rate:.1f}%</div></div>
  <div class="card"><div class="label">Successes</div><div class="value green">{total_success}</div></div>
  <div class="card"><div class="label">Failures</div><div class="value red">{total_failure}</div></div>
  <div class="card"><div class="label">Aborted</div><div class="value yellow">{total_aborted}</div></div>
  <div class="card"><div class="label">Total Runs</div><div class="value blue">{total_all}</div></div>
</div>

<h2>Per-Job Breakdown</h2>
<table>
<thead><tr><th>Job</th><th>Pass Rate</th><th style="text-align:right">Pass</th><th style="text-align:right">Fail</th><th style="text-align:right">Abort</th><th style="text-align:right">Total</th></tr></thead>
<tbody>{job_rows}</tbody>
</table>

{"<h2>Recent Failures</h2>" + failure_sections if failure_sections else ""}

<div class="footer">Data from Prow API &mdash; limited to recent ~24-48h of jobs. Generated {escape(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))}.</div>
</body>
</html>"""
    return html


def main():
    parser = argparse.ArgumentParser(description="HyperShift presubmit job report from Prow")
    parser.add_argument("--hours", type=int, default=24, help="Number of hours to look back (default: 24)")
    parser.add_argument("--since", type=str, help="Start time in ISO format (e.g. 2026-03-18T00:00:00Z)")
    parser.add_argument("--until", type=str, help="End time in ISO format (default: now)")
    parser.add_argument("--format", choices=["html", "markdown", "json"], default="html", help="Output format")
    parser.add_argument("--output", "-o", type=str, help="Output file path (default: stdout)")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)

    if args.since:
        since = datetime.fromisoformat(args.since.replace("Z", "+00:00"))
    else:
        since = now - timedelta(hours=args.hours)

    if args.until:
        until = datetime.fromisoformat(args.until.replace("Z", "+00:00"))
    else:
        until = now

    print(f"Fetching prowjobs from Prow API...", file=sys.stderr)
    items = fetch_prowjobs()
    print(f"  Fetched {len(items)} total prowjobs", file=sys.stderr)

    jobs = filter_hypershift_presubmit(items, since, until)
    print(f"  Found {len(jobs)} hypershift presubmit jobs on main", file=sys.stderr)

    if not jobs:
        print("No matching jobs found in the specified time range.", file=sys.stderr)
        print("Note: The Prow API only retains ~24-48h of recent jobs.", file=sys.stderr)
        sys.exit(0)

    agg = aggregate(jobs)

    if args.format == "html":
        output = render_html(agg, since, until, jobs)
    elif args.format == "markdown":
        output = render_markdown(agg, since, until, jobs)
    else:
        output = json.dumps({
            "period": {"since": since.isoformat(), "until": until.isoformat()},
            "overall": {
                "total": sum(v["total"] for v in agg.values()),
                "success": sum(v["success"] for v in agg.values()),
                "failure": sum(v["failure"] for v in agg.values()),
                "aborted": sum(v["aborted"] for v in agg.values()),
                "pass_rate": round(sum(v["success"] for v in agg.values()) / max(sum(v["success"] + v["failure"] for v in agg.values()), 1) * 100, 1),
            },
            "jobs": {name: counts for name, counts in sorted(agg.items())},
            "failures": [j for j in jobs if j["state"] == "failure"],
        }, indent=2)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
