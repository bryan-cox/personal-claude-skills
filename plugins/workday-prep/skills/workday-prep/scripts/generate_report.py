#!/usr/bin/env python3
"""Generate a Bootstrap 5 HTML workday report from workday-data.json."""

import json
import sys
from datetime import datetime

PRIORITY_CONFIG = {
    "Blocker":  {"badge": "danger",  "icon": "&#9888;"},
    "Critical": {"badge": "danger",  "icon": "&#9888;"},
    "Major":    {"badge": "warning", "icon": "&#9650;"},
    "Normal":   {"badge": "info",    "icon": "&#9679;"},
    "Minor":    {"badge": "secondary","icon": "&#9661;"},
}

def action_badge(action, is_draft=False):
    if action == "review":
        return '<span class="badge bg-purple">Needs your review</span>'
    if is_draft:
        return '<span class="badge bg-secondary">Your draft PR</span>'
    return '<span class="badge bg-success">Your PR &mdash; follow up</span>'

def status_badge(status):
    s = (status or "").lower()
    if s in ("done", "closed", "resolved"):
        cls = "success"
    elif "progress" in s:
        cls = "primary"
    elif s in ("to do", "new", "open"):
        cls = "secondary"
    else:
        cls = "info"
    return f'<span class="badge bg-{cls}">{status}</span>'

def pr_row(pr):
    repo = pr.get("repo", "")
    num = pr.get("number", "")
    title = pr.get("title", "")
    url = pr.get("url", "")
    is_draft = pr.get("isDraft", False)
    act = pr.get("action", "followup")
    draft_label = ' <span class="text-muted fst-italic">(draft)</span>' if is_draft else ""
    return f"""
    <tr>
      <td>{action_badge(act, is_draft)}</td>
      <td><a href="{url}" target="_blank">#{num}</a> {title}{draft_label}</td>
      <td class="text-muted small">{repo}</td>
    </tr>"""

def render_group(group):
    priority = group["priority"]
    items = group.get("items", [])
    cfg = PRIORITY_CONFIG.get(priority, {"badge": "light", "icon": "&#9679;"})
    rows = []
    for item in items:
        jira_key = item.get("jira_key", "")
        jira_summary = item.get("jira_summary", "")
        jira_status = item.get("jira_status", "")
        jira_url = f"https://issues.redhat.com/browse/{jira_key}"
        prs = item.get("prs", [])
        rows.append(f"""
      <div class="card mb-3">
        <div class="card-body">
          <div class="d-flex justify-content-between align-items-start">
            <div>
              <h6 class="card-title mb-1">
                <a href="{jira_url}" target="_blank" class="text-decoration-none">{jira_key}</a>
                &mdash; {jira_summary}
              </h6>
            </div>
            <div>{status_badge(jira_status)}</div>
          </div>
          {"<table class='table table-sm table-borderless mt-2 mb-0'><tbody>" + "".join(pr_row(pr) for pr in prs) + "</tbody></table>" if prs else '<p class="text-muted small mt-2 mb-0">No linked PRs</p>'}
        </div>
      </div>""")

    if not rows:
        return ""

    return f"""
    <div class="mb-4">
      <h4><span class="badge bg-{cfg['badge']}">{cfg['icon']} {priority}</span>
        <span class="text-muted small ms-2">{len(items)} item{"s" if len(items) != 1 else ""}</span>
      </h4>
      {"".join(rows)}
    </div>"""

def render_unlinked(prs):
    if not prs:
        return ""
    rows = "".join(pr_row(pr) for pr in prs)
    return f"""
    <div class="mb-4">
      <h4><span class="badge bg-light text-dark">Uncategorized</span>
        <span class="text-muted small ms-2">{len(prs)} PR{"s" if len(prs) != 1 else ""}</span>
      </h4>
      <div class="card mb-3"><div class="card-body">
        <table class="table table-sm table-borderless mb-0"><tbody>{rows}</tbody></table>
      </div></div>
    </div>"""

def main():
    if len(sys.argv) < 3:
        print("Usage: generate_report.py <data.json> <output.html>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    generated = data.get("generated", datetime.now(tz=None).isoformat())
    groups = data.get("groups", [])
    unlinked = data.get("unlinked_prs", [])

    priority_order = ["Blocker", "Critical", "Major", "Normal", "Minor"]
    sorted_groups = sorted(groups, key=lambda g: priority_order.index(g["priority"]) if g["priority"] in priority_order else 99)

    total_prs_review = sum(
        1 for g in groups for item in g.get("items", []) for pr in item.get("prs", []) if pr.get("action") == "review"
    ) + sum(1 for pr in unlinked if pr.get("action") == "review")
    total_prs_followup = sum(
        1 for g in groups for item in g.get("items", []) for pr in item.get("prs", []) if pr.get("action") == "followup"
    ) + sum(1 for pr in unlinked if pr.get("action") == "followup")
    total_jira = sum(len(g.get("items", [])) for g in groups)

    group_html = "".join(render_group(g) for g in sorted_groups)
    unlinked_html = render_unlinked(unlinked)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workday Prep</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background: #f8f9fa; }}
    .bg-purple {{ background-color: #6f42c1 !important; }}
    .card {{ border-left: 3px solid #dee2e6; }}
    .badge {{ font-size: 0.75em; }}
    a {{ color: #0d6efd; }}
    a:hover {{ color: #0a58ca; }}
  </style>
</head>
<body>
  <div class="container py-4" style="max-width: 900px;">
    <div class="d-flex justify-content-between align-items-center mb-4">
      <h1 class="mb-0">Workday Prep</h1>
      <span class="text-muted">Generated {generated}</span>
    </div>

    <div class="row mb-4">
      <div class="col-md-4">
        <div class="card text-center">
          <div class="card-body">
            <h2 class="mb-0">{total_prs_review}</h2>
            <small class="text-muted">PRs to review</small>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center">
          <div class="card-body">
            <h2 class="mb-0">{total_prs_followup}</h2>
            <small class="text-muted">Your PRs to follow up</small>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center">
          <div class="card-body">
            <h2 class="mb-0">{total_jira}</h2>
            <small class="text-muted">Jira issues</small>
          </div>
        </div>
      </div>
    </div>

    {group_html}
    {unlinked_html}

    <footer class="text-center text-muted small mt-5 mb-3">
      Generated by workday-prep skill
    </footer>
  </div>
</body>
</html>"""

    with open(sys.argv[2], "w") as f:
        f.write(html)

    print(f"Report written to {sys.argv[2]}")
    print(f"{total_prs_review} PRs to review, {total_prs_followup} PRs to follow up, {total_jira} Jira issues")

if __name__ == "__main__":
    main()
