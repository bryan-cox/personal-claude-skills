---
name: update-worklog
description: Use when the user wants their Obsidian worklog populated from GitHub PRs and Jira activity, asks to update or populate the worklog, asks what they did on a date, or wants PR activity logged.
---

# Populate Worklog from GitHub and Jira

Collects GitHub PR activity and the user's Jira comments, worklogs, transitions, and field changes for a date window. The AI merges both sources by Jira key so one piece of work appears once in the Obsidian daily note.

## Arguments

```
/update-worklog [--date YYYY-MM-DD] [--dry-run]
```

- `--date`: date to populate (default: today)
- `--dry-run`: preview the merged entries without writing

## Scripts

All scripts live in the plugin's `scripts/` directory. Resolve the path:

```bash
SCRIPTS="$(dirname "$(dirname "$(cd "$(dirname "$0")" && pwd)")")/scripts"
```

Or use `~/.claude/plugins/worklog/scripts/` when running from the installed plugin.

## Workflow

### 1. Determine the activity window

Set `TARGET_DATE` from `--date` or today's date. Read the existing note at `~/Red Hat/Work log/YYYY/MM/YYYY-MM-DD.md` and capture its `*Last updated: ...*` timestamp, if present. Use that exact timestamp as the strict lower bound for both sources. If the note or timestamp is absent, collect activity from the start of `TARGET_DATE`. The upper bound is now for today, or the end of `TARGET_DATE` for a past date.

### 2. Collect GitHub activity

Run the existing scripts:

```bash
python3 ${SCRIPTS}/fetch-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}] \
  | python3 ${SCRIPTS}/classify-prs.py --date ${TARGET_DATE} [--since ${LAST_UPDATED}]
```

`fetch-prs.py` searches authored, reviewed, and commented PRs. `classify-prs.py` verifies activity timestamps, filters CI retrigger commands, groups authored work by Jira key, and creates the separate code-review task.

### 3. Collect Jira activity

Use the Atlassian Jira MCP tools; do not infer Jira activity from issue `updated` timestamps alone.

1. Call `atlassianUserInfo` and use its `account_id` as the current user.
2. Call `getAccessibleAtlassianResources` to resolve the Jira `cloudId`. Use that ID for the JQL search and issue reads. Search with `searchJiraIssuesUsingJql`, using this JQL and `maxResults: 100`. Use a one-day cushion around the UTC window when computing the JQL dates; the precise UTC filter below removes the extra candidates.

   ```text
   (issuekey in updatedBy("<account_id>", "<since-date>", "<target-date>")
    OR (worklogAuthor = currentUser()
        AND worklogDate >= "<since-date>"
        AND worklogDate <= "<target-date>"))
   ORDER BY updated DESC
   ```

   Use one day before the lower-bound date for `<since-date>` and one day after `TARGET_DATE` for `<target-date>` to absorb Jira timezone and date-granularity differences. Follow every `nextPageToken` until none remains. This JQL finds candidate issues; it does not prove that each change was made by the user.
3. For every candidate, call `getJiraIssue` with `fields: ["summary", "status", "comment", "worklog"]` and `expand: "changelog"`.
4. Keep only events authored or updated by the current account ID and within the exact activity window:
   - comments: match `author.accountId` or `updateAuthor.accountId`; use `created` or `updated` respectively
   - worklogs: match `author.accountId` or `updateAuthor.accountId`; use `created` or `updated` for when the log was entered/edited, and retain `started` for when the work occurred
   - issue changes: match `changelog.histories[].author.accountId`; use the history's `created` time and summarize its changed fields

   Normalize Jira timestamps and `LAST_UPDATED` to UTC. Include events strictly after `LAST_UPDATED` and no later than the activity-window end. When no `LAST_UPDATED` exists, include the target date's activity. `updatedBy` is date-granular, so this timestamp check is required for incremental runs.
5. Ignore comments containing `Generated via TaskLedger /update-jira`; they are generated status reports, not new worklog activity. Check pagination metadata for comments, worklogs, and changelog. If Jira reports more records than it returned and the missing page could overlap the activity window, tell the user the Jira scan is incomplete instead of claiming a full cross-reference.

Keep restricted Jira details within the local worklog. Jira access for this workflow does not authorize publishing issue details to public reports or other channels.

### 4. Merge and deduplicate

Turn meaningful Jira events into task descriptions, including the event type when useful (for example, a worklog duration or a status transition). Use the Jira summary as the title for Jira-only work. Map the current Jira status category `done` to `completed`; map other categories to `in progress`. Do not invent next steps from Jira activity.

Before previewing, merge Jira-derived tasks into the GitHub classifier's `authored_tasks`:

- Join on Jira key, case-insensitively. Keep one task per Jira key, combining distinct descriptions and PR URLs.
- If GitHub already has that key, add Jira context to that task instead of creating a second task. Jira-only issues become new tasks.
- Remove exact and semantic duplicates across comments, worklogs, changelog events, and PR descriptions. Keep the most informative wording once.
- When current Jira status and an associated PR disagree, keep the task `in progress` if either the Jira status is not done or any associated PR remains open.
- Keep `review_task` as the separate Code Reviews section; do not duplicate PR reviews as Jira work items.

Jira-derived task objects use the classifier schema: `jira_ticket`, `title`, `descriptions`, `status` (`completed` or `in progress`), `upnext_description`, and `github_pr` or `github_prs`. Leave `upnext_description` empty unless Jira or GitHub supplied an explicit next step.

The writer coalesces repeated Jira keys as a safeguard and merges new descriptions/PR links into an existing task section for that Jira key. It updates the section in place rather than adding a duplicate heading.

### 5. Preview and confirm

Show counts for GitHub-authored tasks, Jira issues with activity, and PR reviews. Preview the merged task groups by Jira key, including Jira-only work, and call out any Jira scan limits. If `--dry-run`, stop without writing. Otherwise ask the user to confirm the merged preview.

### 6. Write the Obsidian note

Write the merged classifier JSON (`authored_tasks` plus `review_task`) to a temporary file, then pass it to the writer:

```bash
python3 ${SCRIPTS}/write-obsidian.py --date ${TARGET_DATE} [--dry-run] < /path/to/merged-tasks.json
```

The writer deduplicates descriptions and PR links against matching Jira sections in the existing note, merges new activity into those sections, and retains the separate Code Reviews section.

### 7. Report

Report the work window, GitHub and Jira activity counts, Jira keys merged, new task sections, existing sections updated, duplicates skipped, and any incomplete Jira results. If incremental, include the `LAST_UPDATED` timestamp used.
