---
name: status-update
description: Use when generating a biweekly work report, a Slack-ready status HTML page, or Jira status comments; also use when the user asks for a status update or to post status.
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

Generates a local HTML work report and a Slack-ready HTML page, commits and pushes a dated Scrum Markdown report, and posts Jira comments only after user confirmation. Obsidian is the default data source.

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

1. **Calculate the reporting dates** using the table above. Set `START_DATE` to the most recent Tuesday or Thursday strictly before today and `END_DATE` to today. Format both as `YYYY-MM-DD`.

2. **Generate the local work report**:
   - Obsidian is the default source. Do not pass an `--obsidian` flag.
   - Use an explicit output path so the command does not overwrite `weekly-report.html`:
      ```
      /taskledger:html-report --start-date {START_DATE} --end-date {END_DATE} --output ~/worklog/{START_DATE}-to-{END_DATE}-work-report.html --no-open
      ```
   - If `--file PATH` was passed explicitly:
      ```
      /taskledger:html-report --file {PATH} --start-date {START_DATE} --end-date {END_DATE} --output ~/worklog/{START_DATE}-to-{END_DATE}-work-report.html --no-open
      ```
   - Pass `--no-open` so the report is written without launching a browser. The Slack page in step 4 is the only artifact that opens.
   - If the slash command is unavailable, follow `~/bryan-cox/taskledger/plugins/taskledger/commands/html-report.md` and pass `--no-open`.

3. **Commit scrum status to repo**:
   - Use the `--scrum-repo` path (default: `~/bryan-cox/scrum-status`)
   - Derive the GitHub remote URL from the repo's `git remote get-url origin` (e.g., `https://github.com/bryan-cox/scrum-status.git` → `https://github.com/bryan-cox/scrum-status`)
   - Generate a scrum status markdown file at `{scrum-repo}/{today}-hypershift-scrum-status.md` following the format of existing files in that repo (JIRA-linked sections with descriptions and PRs under "🦀 Things I've been working on" and "⭐ Things I plan on working on next", a "Code Reviews" section listing reviewed/commented PRs with total count for the period, plus a "Non-feature work" / "CI Infrastructure" section and a footer link)
   - Stage only `{today}-hypershift-scrum-status.md` by its exact path. Leave `.html` files and other untracked files untouched.
   - Commit only the `.md` file.
   - Commit message: `Add HyperShift scrum status report for {today}`
   - Push to remote

4. **Generate and open the Slack summary page**:
   Write `{scrum-repo}/{today}-hypershift-slack-status.html` so the user can copy its rendered text into Slack. Use the dolphin blog format: concise, conversational paragraphs, not bullets. Include:
   - `**🦀 Things I've been working on**` header followed by a paragraph of **4-5 sentences max**. Prioritize: bug fixes, items that affect the whole team (CI reliability, shared tooling, test infrastructure), and merged PRs. Reference JIRA ticket IDs inline. Omit low-impact or routine items — the full status link covers those.
   - `**⭐ Things I plan on working on next**` header followed by a short paragraph summarizing upcoming work
   - A footer link: `[Full, detailed status available here]({github-remote-url}/blob/main/{today}-hypershift-scrum-status.md)` where `{github-remote-url}` is derived from the scrum repo's git remote in step 3
   - Keep the page easy to copy with selectable text, paragraph breaks, and clickable links.
   - Use bold paragraphs for section headers instead of HTML heading tags, so Slack preserves the formatting when pasted.
   - Open the HTML file in the default browser. Leave it uncommitted; only the Markdown report is pushed.
   - In chat, report the page path and that it opened. Do not repeat the full summary unless the user asks.
   - Use the daily worklog and public PR metadata for published content. Do not copy raw Jira comments, worklogs, or changelog details into the Scrum report or Slack page.

5. **Prepare Jira status comments**:
   - By default (no `--file` flag):
      ```
      /taskledger:update-jira --start-date {START_DATE} --end-date {END_DATE}
      ```
   - If `--file PATH` was passed explicitly:
      ```
      /taskledger:update-jira --file {PATH} --start-date {START_DATE} --end-date {END_DATE}
      ```
   - Obsidian is the default source. Do not pass an `--obsidian` flag.
   - Follow the update-jira duplicate check and preview. Post comments only after the user explicitly confirms. If the user cancels or redirects the task before confirming, leave comments unposted and report them as pending.
   - If the slash command is unavailable, follow `~/bryan-cox/taskledger/plugins/taskledger/commands/update-jira.md`.

6. **Report** `START_DATE` and `END_DATE`, the report paths, the Markdown commit and push result, whether the Slack page opened, and the Jira-comment result. Mark each step as completed, pending, or skipped. Do not say all steps completed while Jira comments are pending.
