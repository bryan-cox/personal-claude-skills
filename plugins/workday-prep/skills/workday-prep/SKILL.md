---
name: workday-prep
description: Generate a prioritized morning workday report with GitHub PRs and Jira issues. Use when user says "prep my day", "workday prep", "morning report", "what do I need to work on", or "start my day".
---

# Workday Prep

## Quick start

Run `/workday-prep` to generate an HTML report at `/tmp/workday.html` and open it in the browser.

Each row has a checkbox. Checking one dims and strikes the row, and the same item
stays in sync between the Top Priorities table and its tab. Check state is scoped
to a single report build (`localStorage` key `workday-prep-done:<generated>`), so
**every new run starts unchecked**; refreshing the same page keeps your marks.
Stale keys from earlier runs are pruned on load. If `localStorage` is unavailable
(Safari on `file://`), checkboxes still work for the life of the page.

## Prerequisites

- `gh` CLI authenticated (`gh auth status`)
- `acli` CLI with env vars: `JIRA_URL`, `JIRA_API_TOKEN`, `EMAIL` (auto-authenticates on first run)

## Workflow

Locate this skill's `scripts/` directory (search for `generate_report.py` in the plugin install location). Then run all phases using those scripts.

### Phase 1: Fetch Data (parallel)

Run both scripts **in parallel**:

```bash
python3 {SKILL_DIR}/scripts/fetch_github.py > /tmp/workday-gh.json
```

```bash
python3 {SKILL_DIR}/scripts/fetch_jira.py > /tmp/workday-jira.json
```

`fetch_github.py` — queries `gh search prs` for review-requested and authored open PRs, extracts Jira keys.
`fetch_jira.py` — queries `acli jira workitem search` for all unresolved issues assigned to you.

If either script fails with an auth error, instruct the user to authenticate first.

If `fetch_github.py` exits non-zero, a GitHub query failed and it wrote **no**
output (it already retries once internally). Re-run the fetch. Never build a
report from a partial or stale `/tmp/workday-gh.json` — a failed query would
otherwise render as an empty review queue, indistinguishable from a quiet day.

### Phase 1.5: Supplement Jira Data

After both Phase 1 scripts complete, fetch priorities for PR-referenced Jira issues not in the user's assigned set:

```bash
python3 {SKILL_DIR}/scripts/fetch_jira_supplement.py
```

This reads both JSON files, finds Jira keys from PRs that aren't in the assigned issues, fetches their priority/status via `acli`, and merges them into `/tmp/workday-jira.json` with `_supplemental: true`.

### Phase 2: Build Data JSON

```bash
python3 {SKILL_DIR}/scripts/build_data.py
```

Reads both Phase 1 files and writes `/tmp/workday-data.json`. It:

1. Parse `/tmp/workday-jira.json` — array of `{key, summary, status, priority}`
2. Parse `/tmp/workday-gh.json` — array of `{url, title, number, repo, isDraft, jira, action, updatedAt}`
3. Match PRs to Jira issues by `jira` key
4. Group by priority: Blocker, Critical, Major, Normal, Minor
5. Jira issues with no linked PRs get an empty `prs` array
6. PRs with no Jira match (no Jira key extracted at all) go in `unlinked_prs`
7. Copy the Jira issues list into `jira_issues`, excluding any with `_supplemental: true` (only your assigned issues, not issues referenced by other people's PRs)

Write the result matching the JSON format below.

### Skip a duplicate scheduled run

If this run was triggered by a schedule rather than an explicit user request, and
the newest `/tmp/workday-*.html` archive is less than 60 minutes old, **skip the
whole workflow** and tell the user the existing report is still current. This
stops a scheduled run from duplicating — and re-opening, and wiping the marks in —
a report the user is actively working in. An explicit request always runs.

### Phase 3: Generate and Open

```bash
python3 {SKILL_DIR}/scripts/generate_report.py /tmp/workday-data.json /tmp/workday.html && open /tmp/workday.html
```

`generate_report.py` also writes a timestamped copy (`/tmp/workday-YYYY-MM-DD-HHMM.html`,
newest 30 kept) because `/tmp/workday.html` is overwritten on every run — the
archive is the only evidence a given run happened.

Then send a desktop notification so a scheduled run is never silently missed:

```bash
osascript -e 'display notification "X PRs to review, Y to follow up, Z Jira issues" with title "Workday Prep" sound name "Glass"'
```

Print: "X PRs to review, Y PRs to follow up, Z Jira issues — report opened in browser"

## JSON Data Format

```json
{
  "generated": "2026-05-17T09:00:00Z",
  "groups": [
    {
      "priority": "Blocker",
      "items": [
        {
          "jira_key": "PROJ-123",
          "jira_summary": "Issue title",
          "jira_status": "In Progress",
          "prs": [
            {"url": "https://github.com/org/repo/pull/1", "title": "PR title", "action": "review", "number": 1, "repo": "org/repo", "isDraft": false, "updatedAt": "2026-05-17T09:00:00Z"}
          ]
        }
      ]
    }
  ],
  "unlinked_prs": [
    {"url": "...", "title": "...", "action": "review", "number": 1, "repo": "org/repo", "isDraft": false}
  ],
  "jira_issues": [
    {"key": "PROJ-123", "summary": "Issue title", "status": "In Progress", "priority": "Blocker"}
  ]
}
```

Priority order: Blocker > Critical > Major > Normal > Minor > Uncategorized.
