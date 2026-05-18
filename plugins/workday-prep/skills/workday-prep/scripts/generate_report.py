#!/usr/bin/env python3
"""Generate a tabbed Bootstrap 5 HTML workday report from workday-data.json."""

import json
import sys
from collections import defaultdict
from datetime import datetime

PRIORITY_ORDER = ["Blocker", "Critical", "Major", "Normal", "Minor"]

ICON_GH = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 16 16" style="vertical-align:text-bottom"><path fill="#24292f" d="M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66.07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27.68 0 1.36.09 2 .27 1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 0 .21.15.46.55.38A8.013 8.013 0 0016 8c0-4.42-3.58-8-8-8z"/></svg>'
ICON_PR = '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 16 16" style="vertical-align:text-bottom"><path fill="#1a7f37" d="M1.5 3.25a2.25 2.25 0 1 1 3 2.122v5.256a2.251 2.251 0 1 1-1.5 0V5.372A2.25 2.25 0 0 1 1.5 3.25Zm5.677-.177L9.573.677A.25.25 0 0 1 10 .854V2.5h1A2.5 2.5 0 0 1 13.5 5v5.628a2.251 2.251 0 1 1-1.5 0V5a1 1 0 0 0-1-1h-1v1.646a.25.25 0 0 1-.427.177L7.177 3.427a.25.25 0 0 1 0-.354ZM3.75 2.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm0 9.5a.75.75 0 1 0 0 1.5.75.75 0 0 0 0-1.5Zm8.25.75a.75.75 0 1 0 1.5 0 .75.75 0 0 0-1.5 0Z"/></svg>'

PRIORITY_BADGE = {
    "Blocker":  "danger",
    "Critical": "danger",
    "Major":    "warning",
    "Normal":   "info",
    "Minor":    "secondary",
}


def relative_time(iso_str):
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(tz=dt.tzinfo)
        delta = now - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return "just now"
        if secs < 3600:
            m = secs // 60
            return f"{m}m ago"
        if secs < 86400:
            h = secs // 3600
            return f"{h}h ago"
        d = secs // 86400
        return f"{d}d ago"
    except (ValueError, TypeError):
        return ""


def priority_sort_key(priority):
    try:
        return PRIORITY_ORDER.index(priority)
    except ValueError:
        return 99


def priority_pill(priority):
    cls = PRIORITY_BADGE.get(priority, "light")
    return f'<span class="badge bg-{cls}">{priority}</span>'


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


def render_pr_groups(prs):
    if not prs:
        return '<p class="text-muted mt-3">No PRs in this category.</p>'

    grouped = defaultdict(list)
    for pr in prs:
        grouped[pr.get("_jira_priority", "") or "Uncategorized"].append(pr)

    order = [p for p in PRIORITY_ORDER if p in grouped]
    if "Uncategorized" in grouped:
        order.append("Uncategorized")

    sections = []
    for priority in order:
        items = sorted(grouped[priority], key=lambda p: p.get("updatedAt", ""))
        cls = PRIORITY_BADGE.get(priority, "dark")
        rows = []
        for pr in items:
            num = pr.get("number", "")
            title = pr.get("title", "")
            url = pr.get("url", "")
            repo = pr.get("repo", "")
            is_draft = pr.get("isDraft", False)
            jira_key = pr.get("_jira_key", "")
            updated = relative_time(pr.get("updatedAt", ""))

            draft = ' <span class="badge bg-secondary ms-1">draft</span>' if is_draft else ""
            jira_cell = ""
            if jira_key:
                jira_url = f"https://issues.redhat.com/browse/{jira_key}"
                jira_cell = f'<a href="{jira_url}" target="_blank" title="{jira_key}" class="text-decoration-none"><img src="https://issues.redhat.com/favicon.ico" alt="" style="width:14px;height:14px;vertical-align:text-bottom"> {jira_key}</a>'

            rows.append(f"""        <tr>
          <td class="text-nowrap">{ICON_GH} {repo}</td>
          <td><a href="{url}" target="_blank" class="text-decoration-none">{ICON_PR} #{num} {title}</a>{draft}</td>
          <td class="text-nowrap">{jira_cell}</td>
          <td class="text-muted text-nowrap">{updated}</td>
        </tr>""")

        sections.append(f"""<div class="card shadow-sm mb-3">
  <div class="card-header py-2 d-flex align-items-center gap-2">
    <span class="badge bg-{cls}">{priority}</span>
    <span class="text-muted small">{len(items)} PR{"s" if len(items) != 1 else ""}</span>
  </div>
  <div class="card-body p-0">
    <table class="table table-hover table-fixed align-middle mb-0">
      <thead class="table-light">
        <tr><th style="width:15%">Repo <span class="sort-arrow">&#9650;</span></th><th style="width:55%">Pull Request <span class="sort-arrow">&#9650;</span></th><th style="width:18%">Jira <span class="sort-arrow">&#9650;</span></th><th style="width:12%">Updated <span class="sort-arrow">&#9650;</span></th></tr>
      </thead>
      <tbody>
{"".join(rows)}
      </tbody>
    </table>
  </div>
</div>""")

    return "\n".join(sections)


def render_top_priorities(review_prs, followup_prs, jira_issues, limit=8):
    items = []
    jira_keys_with_prs = set()
    for pr in review_prs:
        p = pr.get("_jira_priority", "") or "Uncategorized"
        jira_key = pr.get("_jira_key", "")
        if jira_key:
            jira_keys_with_prs.add(jira_key)
        items.append((priority_sort_key(p), p, "review",
            f'{ICON_PR} <a href="{pr.get("url","")}" target="_blank" class="text-decoration-none">#{pr.get("number","")} {pr.get("title","")}</a>',
            "Review PR"))
    for pr in followup_prs:
        p = pr.get("_jira_priority", "") or "Uncategorized"
        jira_key = pr.get("_jira_key", "")
        if jira_key:
            jira_keys_with_prs.add(jira_key)
        items.append((priority_sort_key(p), p, "followup",
            f'{ICON_PR} <a href="{pr.get("url","")}" target="_blank" class="text-decoration-none">#{pr.get("number","")} {pr.get("title","")}</a>',
            "Follow up"))
    for issue in jira_issues:
        key = issue.get("key", "")
        if key in jira_keys_with_prs:
            continue
        p = issue.get("priority", "Normal")
        items.append((priority_sort_key(p), p, "jira",
            f'<a href="https://issues.redhat.com/browse/{key}" target="_blank" class="text-decoration-none"><img src="https://issues.redhat.com/favicon.ico" alt="" style="width:12px;height:12px;vertical-align:text-bottom"> {key}</a> {issue.get("summary","")}',
            issue.get("status", "")))

    items.sort(key=lambda x: x[0])
    items = items[:limit]

    if not items:
        return ""

    TYPE_BADGE = {"review": ("purple", "Review PR"), "followup": ("success", "Your PR"), "jira": ("info", "Jira")}
    rows = []
    for i, (_, priority, kind, desc, extra) in enumerate(items, 1):
        cls = PRIORITY_BADGE.get(priority, "dark")
        type_cls, type_label = TYPE_BADGE.get(kind, ("secondary", kind))
        rows.append(f"""        <tr>
          <td class="text-center text-muted fw-bold" style="width:3%">{i}</td>
          <td style="width:10%"><span class="badge bg-{cls}">{priority}</span></td>
          <td style="width:10%"><span class="badge bg-{type_cls}">{type_label}</span></td>
          <td>{desc}</td>
        </tr>""")

    return f"""<div class="card shadow-sm mb-4 border-start border-primary border-3">
  <div class="card-header py-2 bg-white">
    <strong>Top Priorities</strong> <span class="text-muted small">— work on these first</span>
  </div>
  <div class="card-body p-0">
    <table class="table table-hover align-middle mb-0">
      <tbody>
{"".join(rows)}
      </tbody>
    </table>
  </div>
</div>"""


def render_jira_groups(issues):
    if not issues:
        return '<p class="text-muted mt-3">No Jira issues assigned.</p>'

    grouped = defaultdict(list)
    for issue in issues:
        grouped[issue.get("priority", "Normal")].append(issue)

    order = [p for p in PRIORITY_ORDER if p in grouped]

    sections = []
    for priority in order:
        items = grouped[priority]
        cls = PRIORITY_BADGE.get(priority, "dark")
        rows = []
        for issue in items:
            key = issue.get("key", "")
            summary = issue.get("summary", "")
            status = issue.get("status", "")
            url = f"https://issues.redhat.com/browse/{key}"

            rows.append(f"""        <tr>
          <td><a href="{url}" target="_blank" class="text-decoration-none">{key} {summary}</a></td>
          <td class="text-end text-nowrap">{status_badge(status)}</td>
        </tr>""")

        sections.append(f"""<div class="card shadow-sm mb-3">
  <div class="card-header py-2 d-flex align-items-center gap-2">
    <span class="badge bg-{cls}">{priority}</span>
    <span class="text-muted small">{len(items)} issue{"s" if len(items) != 1 else ""}</span>
  </div>
  <div class="card-body p-0">
    <table class="table table-hover table-fixed align-middle mb-0">
      <thead class="table-light">
        <tr><th style="width:85%">Issue <span class="sort-arrow">&#9650;</span></th><th style="width:15%" class="text-end">Status <span class="sort-arrow">&#9650;</span></th></tr>
      </thead>
      <tbody>
{"".join(rows)}
      </tbody>
    </table>
  </div>
</div>""")

    return "\n".join(sections)


def main():
    if len(sys.argv) < 3:
        print("Usage: generate_report.py <data.json> <output.html>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        data = json.load(f)

    generated = data.get("generated", datetime.now(tz=None).isoformat())
    groups = data.get("groups", [])
    unlinked = data.get("unlinked_prs", [])

    review_prs = []
    followup_prs = []
    for g in groups:
        for item in g.get("items", []):
            for pr in item.get("prs", []):
                enriched = {**pr, "_jira_key": item["jira_key"], "_jira_priority": g["priority"]}
                if pr.get("action") == "review":
                    review_prs.append(enriched)
                else:
                    followup_prs.append(enriched)
    for pr in unlinked:
        enriched = {**pr, "_jira_key": "", "_jira_priority": ""}
        if pr.get("action") == "review":
            review_prs.append(enriched)
        else:
            followup_prs.append(enriched)

    review_prs.sort(key=lambda p: priority_sort_key(p["_jira_priority"]))
    followup_prs.sort(key=lambda p: priority_sort_key(p["_jira_priority"]))

    all_jira = [i for i in data.get("jira_issues", []) if (i.get("status", "").lower() not in ("verified", "closed", "done", "resolved"))]
    if not all_jira:
        for g in sorted(groups, key=lambda g: priority_sort_key(g["priority"])):
            for item in g.get("items", []):
                all_jira.append({
                    "key": item["jira_key"],
                    "summary": item.get("jira_summary", ""),
                    "status": item.get("jira_status", ""),
                    "priority": g["priority"],
                })

    review_html = render_pr_groups(review_prs)
    followup_html = render_pr_groups(followup_prs)
    jira_html = render_jira_groups(all_jira)
    top_html = render_top_priorities(review_prs, followup_prs, all_jira)

    n_review = len(review_prs)
    n_followup = len(followup_prs)
    n_jira = len(all_jira)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Workday Prep</title>
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
  <style>
    body {{ background: #f8f9fa; font-size: .95rem; }}
    .nav-pills .nav-link {{ color: #495057; }}
    .nav-pills .nav-link.active {{ background-color: #0d6efd; }}
    .badge {{ font-size: .75em; }}
    .table th {{ font-size: .8rem; cursor: pointer; user-select: none; }}
    .table th:hover {{ background: #e9ecef; }}
    .table th .sort-arrow {{ font-size: .6em; margin-left: .3em; color: #adb5bd; }}
    .table th.sorted .sort-arrow {{ color: #212529; }}
    .table td {{ font-size: .85rem; }}
    .table-fixed {{ table-layout: fixed; }}
    .table-fixed td:first-child {{ overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .bg-purple {{ background-color: #6f42c1 !important; }}
    a {{ color: #0d6efd; }}
    a:hover {{ color: #0a58ca; }}
  </style>
</head>
<body>
  <div class="container-fluid py-4" style="max-width: 90%;">
    <div class="d-flex justify-content-between align-items-center mb-3">
      <h4 class="mb-0 fw-bold">Workday Prep</h4>
      <span class="text-muted" style="font-size:.75rem">{generated}</span>
    </div>

    <div class="row g-2 mb-3">
      <div class="col-md-4">
        <div class="card text-center border-0 shadow-sm">
          <div class="card-body py-2">
            <h3 class="mb-0">{n_review}</h3>
            <small class="text-muted" style="font-size:.75rem">PRs to review</small>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center border-0 shadow-sm">
          <div class="card-body py-2">
            <h3 class="mb-0">{n_followup}</h3>
            <small class="text-muted" style="font-size:.75rem">Your PRs</small>
          </div>
        </div>
      </div>
      <div class="col-md-4">
        <div class="card text-center border-0 shadow-sm">
          <div class="card-body py-2">
            <h3 class="mb-0">{n_jira}</h3>
            <small class="text-muted" style="font-size:.75rem">Jira issues</small>
          </div>
        </div>
      </div>
    </div>

    {top_html}

    <ul class="nav nav-pills mb-3" role="tablist">
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="review-tab" data-bs-toggle="pill" data-bs-target="#review-pane" type="button" role="tab">PRs to Review <span class="badge bg-light text-dark ms-1">{n_review}</span></button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="mine-tab" data-bs-toggle="pill" data-bs-target="#mine-pane" type="button" role="tab">My PRs to Review <span class="badge bg-light text-dark ms-1">{n_followup}</span></button>
      </li>
      <li class="nav-item" role="presentation">
        <button class="nav-link" id="jira-tab" data-bs-toggle="pill" data-bs-target="#jira-pane" type="button" role="tab">My Jira Issues <span class="badge bg-light text-dark ms-1">{n_jira}</span></button>
      </li>
    </ul>

    <div class="tab-content">
      <div class="tab-pane fade show active" id="review-pane" role="tabpanel">
{review_html}
      </div>
      <div class="tab-pane fade" id="mine-pane" role="tabpanel">
{followup_html}
      </div>
      <div class="tab-pane fade" id="jira-pane" role="tabpanel">
{jira_html}
      </div>
    </div>

    <footer class="text-center text-muted mt-4 mb-2" style="font-size:.7rem">
      Generated by workday-prep
    </footer>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js"></script>
  <script>
  document.querySelectorAll('.table th').forEach(th => {{
    th.addEventListener('click', () => {{
      const table = th.closest('table');
      const tbody = table.querySelector('tbody');
      const idx = Array.from(th.parentNode.children).indexOf(th);
      const rows = Array.from(tbody.querySelectorAll('tr'));
      const arrow = th.querySelector('.sort-arrow');
      const asc = arrow.textContent.trim() === '▲';
      table.querySelectorAll('th').forEach(h => {{
        h.classList.remove('sorted');
        h.querySelector('.sort-arrow').textContent = '▲';
      }});
      th.classList.add('sorted');
      arrow.textContent = asc ? '▼' : '▲';
      rows.sort((a, b) => {{
        let av = a.children[idx].textContent.trim().toLowerCase();
        let bv = b.children[idx].textContent.trim().toLowerCase();
        const an = parseFloat(av), bn = parseFloat(bv);
        if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
        return asc ? av.localeCompare(bv) : bv.localeCompare(av);
      }});
      rows.forEach(r => tbody.appendChild(r));
    }});
  }});
  </script>
</body>
</html>"""

    with open(sys.argv[2], "w") as f:
        f.write(html)

    print(f"Report written to {sys.argv[2]}")
    print(f"{n_review} PRs to review, {n_followup} PRs to follow up, {n_jira} Jira issues")


if __name__ == "__main__":
    main()
