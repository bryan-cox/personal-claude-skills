---
name: workday-prep
description: Generate a prioritized morning workday report with GitHub PRs and Jira issues. Use when user says "prep my day", "workday prep", "morning report", "what do I need to work on", or "start my day".
---

# Workday Prep

## Quick start

Run `/workday-prep` to generate an HTML report at `/tmp/workday.html` and open it in the browser.

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

### Phase 1.5: Supplement Jira Data

After both Phase 1 scripts complete, fetch priorities for PR-referenced Jira issues not in the user's assigned set:

```bash
python3 {SKILL_DIR}/scripts/fetch_jira_supplement.py
```

This reads both JSON files, finds Jira keys from PRs that aren't in the assigned issues, fetches their priority/status via `acli`, and merges them into `/tmp/workday-jira.json` with `_supplemental: true`.

### Phase 2: Build Data JSON

Read both files and build `/tmp/workday-data.json`:

1. Parse `/tmp/workday-jira.json` — array of `{key, summary, status, priority}`
2. Parse `/tmp/workday-gh.json` — array of `{url, title, number, repo, isDraft, jira, action, updatedAt}`
3. Match PRs to Jira issues by `jira` key
4. Group by priority: Blocker, Critical, Major, Normal, Minor
5. Jira issues with no linked PRs get an empty `prs` array
6. PRs with no Jira match (no Jira key extracted at all) go in `unlinked_prs`
7. Copy the Jira issues list into `jira_issues`, excluding any with `_supplemental: true` (only your assigned issues, not issues referenced by other people's PRs)

Write the result matching the JSON format below.

### Phase 3: Generate and Open

```bash
python3 {SKILL_DIR}/scripts/generate_report.py /tmp/workday-data.json /tmp/workday.html && open /tmp/workday.html
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
