---
name: status-update
description: Use when generating biweekly work status reports and posting updates to Jira tickets, or when user says "status update" or "post status"
---

# Status Update

## Synopsis

```
/worklog:status-update [--file PATH] [--scrum-repo PATH]
```

## Arguments

- `--file PATH` _(optional)_: Read worklog data from a local YAML file at `PATH` instead of Obsidian. When passed, `--file PATH` is forwarded to both sub-skill invocations. By default (no flag), Obsidian is used.
- `--scrum-repo PATH` _(optional)_: Path to the local scrum status git repo. Defaults to `~/bryan-cox/scrum-status`.

## Overview

Generates an HTML work report and posts status comments to Jira tickets for the current reporting period. Automatically calculates the start date based on a Tuesday/Thursday biweekly cycle. Obsidian is the default data source.

## Date Calculation

Find the **most recent Tuesday or Thursday strictly before today**:

| Today is    | Start date is     | Days back |
|-------------|-------------------|-----------|
| Monday      | Last Thursday      | 4         |
| Tuesday     | Last Thursday      | 5         |
| Wednesday   | Last Tuesday       | 1         |
| Thursday    | Last Tuesday       | 2         |
| Friday      | Last Thursday      | 1         |
| Saturday    | Last Thursday      | 2         |
| Sunday      | Last Thursday      | 3         |

## Implementation

1. **Calculate the start date** using the table above. Format as `YYYY-MM-DD`.

2. **Invoke the HTML report skill**:
   - By default (no `--file` flag):
     ```
     /taskledger:html-report --obsidian --start-date {calculated-start-date}
     ```
   - If `--file PATH` was passed explicitly:
     ```
     /taskledger:html-report --file {PATH} --start-date {calculated-start-date}
     ```

3. **Commit scrum status to repo**:
   - Use the `--scrum-repo` path (default: `~/bryan-cox/scrum-status`)
   - Derive the GitHub remote URL from the repo's `git remote get-url origin` (e.g., `https://github.com/bryan-cox/scrum-status.git` → `https://github.com/bryan-cox/scrum-status`)
   - Generate a scrum status markdown file at `{scrum-repo}/{today}-hypershift-scrum-status.md` following the format of existing files in that repo (JIRA-linked sections with descriptions and PRs under "🦀 Things I've been working on" and "⭐ Things I plan on working on next", plus a "Non-feature work" section and a footer link)
   - Only commit the `.md` file — do NOT include `.html`
   - Commit message: `Add HyperShift scrum status report for {today}`
   - Push to remote

4. **Generate Slack summary**:
   Present a Slack-ready summary in paragraph form (not bullet points) with:
   - `**🦀 Things I've been working on**` header followed by a paragraph of **4-5 sentences max**. Prioritize: bug fixes, items that affect the whole team (CI reliability, shared tooling, test infrastructure), and merged PRs. Reference JIRA ticket IDs inline. Omit low-impact or routine items — the full status link covers those.
   - `**⭐ Things I plan on working on next**` header followed by a short paragraph summarizing upcoming work
   - A footer link: `[Full, detailed status available here]({github-remote-url}/blob/main/{today}-hypershift-scrum-status.md)` where `{github-remote-url}` is derived from the scrum repo's git remote in step 3

5. **Invoke the Jira update skill**:
   - By default (no `--file` flag):
     ```
     /taskledger:update-jira --obsidian --start-date {calculated-start-date}
     ```
   - If `--file PATH` was passed explicitly:
     ```
     /taskledger:update-jira --file {PATH} --start-date {calculated-start-date}
     ```

6. **Report** the start date used and confirm all steps completed.
