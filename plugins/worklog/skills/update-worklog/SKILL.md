---
name: update-worklog
description: Use when populating the Obsidian worklog with today's work based on GitHub PR activity, or when user says "update worklog", "populate worklog", "what did I do today", or "log my PRs"
---

# Populate Worklog from PRs

Queries GitHub for PR activity (authored, reviewed, commented) on a given date and writes an Obsidian daily note with auto-detected JIRA tickets, contextual descriptions, and inferred status.

## Arguments

```
/update-worklog [--date YYYY-MM-DD] [--dry-run]
```

- `--date`: Date to populate (default: today)
- `--dry-run`: Preview generated entries without writing

## Scripts

All scripts live in the plugin's `scripts/` directory. Resolve the path:

```bash
SCRIPTS="$(dirname "$(dirname "$(cd "$(dirname "$0")" && pwd)")")/scripts"
```

Or simply use the absolute path: `~/.claude/plugins/worklog/scripts/` (installed location) or the repo path if running from source.

## Workflow

### Step 1: Determine parameters

```bash
TARGET_DATE=$(date +%Y-%m-%d)   # or from --date flag
```

Check the existing Obsidian note at `~/Red Hat/Work log/YYYY/MM/YYYY-MM-DD.md` for a `*Last updated: ...*` line. If found, pass it as `--since` for incremental runs.

### Step 2: Fetch PR activity

```bash
python3 ${SCRIPTS}/fetch-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}]
```

This runs three `gh search prs` queries in parallel (author, reviewed-by, commenter), extracts JIRA tickets, deduplicates by URL, and outputs JSON to stdout.

### Step 3: Classify and generate tasks

Pipe the fetch output into the classifier:

```bash
python3 ${SCRIPTS}/fetch-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}] \
  | python3 ${SCRIPTS}/classify-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}]
```

This fetches detailed commit/review/comment activity for authored PRs, verifies review dates for non-authored PRs, filters CI retrigger commands, groups by JIRA ticket, and outputs structured task JSON.

### Step 4: Preview and confirm

Show the user the classified output — how many authored tasks, how many reviews, which JIRA tickets. If `--dry-run`, stop here.

Otherwise, ask the user to confirm before writing.

### Step 5: Write Obsidian note

Pipe the classified output into the writer:

```bash
python3 ${SCRIPTS}/fetch-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}] \
  | python3 ${SCRIPTS}/classify-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}] \
  | python3 ${SCRIPTS}/write-obsidian.py --date ${TARGET_DATE} [--dry-run]
```

This handles merge detection (same-day and cross-date), deduplication against existing entries, formatting, and writes to `~/Red Hat/Work log/YYYY/MM/YYYY-MM-DD.md`.

### Step 6: Report

Show the summary from write-obsidian.py output (tasks added, skipped, merges detected). If incremental, note the last_updated window used.
