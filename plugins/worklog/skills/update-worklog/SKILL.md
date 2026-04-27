---
name: update-worklog
description: Use when populating worklog.yaml with today's work based on GitHub PR activity, or when user says "update worklog", "populate worklog", "what did I do today", or "log my PRs"
---

# Populate Worklog from PRs

## Overview

Queries GitHub for all PR activity (authored, reviewed, commented) on a given date and generates worklog.yaml task entries with contextual descriptions, auto-detected JIRA tickets, and inferred status.

## Arguments

```
/populate-from-prs [--file PATH] [--date YYYY-MM-DD] [--dry-run]
```

- `--file`: Path to worklog.yaml (default: `~/worklog/worklog.yaml`)
- `--date`: Date to populate (default: today's date from system)
- `--dry-run`: Show generated entries without writing to file

## Implementation

Execute the following workflow step by step:

### Phase 1: Parse Arguments and Load Timestamp

Extract from user input:
- `FILE_PATH`: worklog file path (default `~/worklog/worklog.yaml`)
- `TARGET_DATE`: date in `YYYY-MM-DD` format. If not provided, determine today's date by running `date +%Y-%m-%d`
- `DRY_RUN`: boolean (default: false)

**Load incremental timestamp:** Read the existing worklog file and check if the `TARGET_DATE` entry has a `last_updated` field. This ISO 8601 timestamp (e.g., `"2026-04-02T15:22:00Z"`) records when `/update-worklog` last ran for this date.
- If found, store as `LAST_UPDATED` — subsequent phases will only look at activity *after* this timestamp
- If not found (first run for this date), set `LAST_UPDATED` to empty — phases will use date-level filtering (`startswith("{TARGET_DATE}")`)

### Phase 2: Fetch PR Activity

Run these three `gh search` commands **in parallel** using the Bash tool. Each command includes `body` for JIRA ticket detection but pipes through a Python script that extracts the JIRA ticket from the body and then discards the body text to keep output compact and avoid truncation.

```bash
gh search prs --author=@me --updated=">=${TARGET_DATE}" --json number,title,url,state,isDraft,repository,body,updatedAt --limit 1000 | python3 -c "
import sys, json, re
prs = json.load(sys.stdin)
for pr in prs:
    m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('title',''))
    if not m:
        m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('body','') or '')
    pr['jira'] = m.group(0) if m else ''
    pr.pop('body', None)
json.dump(prs, sys.stdout)
"
```

```bash
gh search prs --reviewed-by=@me --updated=">=${TARGET_DATE}" --json number,title,url,state,isDraft,repository,body,updatedAt --limit 1000 | python3 -c "
import sys, json, re
prs = json.load(sys.stdin)
for pr in prs:
    m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('title',''))
    if not m:
        m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('body','') or '')
    pr['jira'] = m.group(0) if m else ''
    pr.pop('body', None)
json.dump(prs, sys.stdout)
"
```

```bash
gh search prs --commenter=@me --updated=">=${TARGET_DATE}" --json number,title,url,state,isDraft,repository,body,updatedAt --limit 1000 | python3 -c "
import sys, json, re
prs = json.load(sys.stdin)
for pr in prs:
    m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('title',''))
    if not m:
        m = re.search(r'[A-Z][A-Z0-9]+-\d+', pr.get('body','') or '')
    pr['jira'] = m.group(0) if m else ''
    pr.pop('body', None)
json.dump(prs, sys.stdout)
"
```

### Phase 3: Deduplicate and Classify

For each unique PR (by URL):

1. **Track activity types** - a single PR may appear in multiple queries:
   - From `--author` query: `authored`
   - From `--reviewed-by` query: `reviewed`
   - From `--commenter` query: `commented`

2. **Detect JIRA ticket** — use the `jira` field already extracted by the Python script in Phase 2. The script checks the PR title first, then the body. If the `jira` field is empty, set `jira_ticket` to `""`.

3. **Split into two buckets**:
   - **Authored PRs**: PRs where the user is the author (appeared in `--author` query)
   - **Review/comment-only PRs**: PRs where the user is NOT the author (appeared only in `--reviewed-by` and/or `--commenter` queries)

#### Authored PRs — fetch detailed activity and generate descriptions

**Important:** The `gh search --author` query returns PRs you authored that were *updated* on `TARGET_DATE`. This does NOT mean *you* did anything — CI, bots, or other users may have triggered the update. You must verify your own activity.

For each authored PR, fetch activity to check for YOUR work and generate specific descriptions. Run these **in parallel** per PR (batch as many as practical).

**Timestamp-aware filtering:** If `LAST_UPDATED` is set, use `> "{LAST_UPDATED}"` to only fetch activity since the last run. If `LAST_UPDATED` is empty (first run), use `startswith("{TARGET_DATE}")` to get all activity for the day.

When `LAST_UPDATED` is **empty** (first run):
```bash
gh api repos/{owner}/{repo}/pulls/{number}/commits --jq '[.[] | select(.commit.author.date | startswith("{TARGET_DATE}")) | .commit.message]'
```

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '[.[] | select(.submitted_at | startswith("{TARGET_DATE}")) | {user: .user.login, state: .state}]'
```

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments --jq '[.[] | select(.user.login == "{USERNAME}") | select(.created_at | startswith("{TARGET_DATE}")) | {user: .user.login, body: .body}]'
```

When `LAST_UPDATED` is **set** (incremental run):
```bash
gh api repos/{owner}/{repo}/pulls/{number}/commits --jq '[.[] | select(.commit.author.date > "{LAST_UPDATED}") | .commit.message]'
```

```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '[.[] | select(.submitted_at > "{LAST_UPDATED}") | {user: .user.login, state: .state}]'
```

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments --jq '[.[] | select(.user.login == "{USERNAME}") | select(.created_at > "{LAST_UPDATED}") | {user: .user.login, body: .body}]'
```

**Filter out CI retrigger commands:** Before checking for activity, discard any comments that are purely CI slash commands (e.g., `/retest`, `/test <job-name>`, `/override <job-name>`). These are not meaningful work activity. Comments like `/jira backport ...`, `/lgtm`, `/approve`, or substantive discussion DO count as activity.

**Exclude authored PRs with no user activity:** If ALL three queries return empty arrays (no commits pushed, no reviews received, no meaningful comments by the user after filtering out CI retrigger commands):
- If the PR is **merged or closed**: do NOT exclude it. Skip description generation, but still pass it through to Phase 5 for merge detection. These "activity-less merged PRs" will be handled by same-day merge detection or merged-on-different-day detection.
- If the PR is **open**: the PR was only updated by CI or other users — **exclude** this PR entirely. Do NOT fall back to a generic description.

For each authored PR **with verified activity**, generate a **separate task**:

1. **Descriptions** — use the fetched activity data to generate a concise, specific summary of what was actually done today. Consider:
   - Commit messages pushed today (most informative source)
   - Reviews received today and whether they were addressed
   - Comments/discussion that happened today
   - PR state changes (merged, marked ready for review, etc.)

   Synthesize this into 1-3 short description strings that read naturally for a work log. Examples:
   - `"Addressed Alberto's review comments on PLS controller logic"`
   - `"Pushed fix for DNS zone pagination and added unit tests"`
   - `"Merged PR after final approval from Seth"`
   - `"Rebased on main and resolved merge conflicts"`

2. **Status**: merged/closed → `"completed"`, open → `"in progress"`

3. **upnext_description** — must ALWAYS be populated for non-completed tasks:
   - Merged: `""` (nothing left to do)
   - Open + is draft: `"Finish implementation, dev test, and mark the PR ready for review"`
   - Open + not draft: `"Get PR reviewed and merged"`
   - Closed (not merged): `""` (abandoned)
   - **Rule:** If `status` is `"in progress"`, `upnext_description` must NEVER be empty. Always provide a meaningful next step.

4. **Build task object**:
   ```yaml
   - jira_ticket: "<detected JIRA or empty>"
     descriptions:
       - "<specific description from activity>"
     status: "<inferred status>"
     upnext_description: "<inferred next step>"
     github_pr: "<PR URL>"
     blocker: ""
   ```

#### Review/comment-only PRs — verify activity date then consolidate

**Important:** The `gh search` queries return PRs where you reviewed/commented at *any point* AND the PR was updated on `TARGET_DATE`. This does NOT mean your activity happened on `TARGET_DATE`. You must verify.

For each non-authored PR, check whether the user actually reviewed or commented within the relevant time window by running **in parallel** (batch as many as practical).

Where `{USERNAME}` is obtained from `gh api user --jq '.login'` (run once, cache the result).

When `LAST_UPDATED` is **empty** (first run):
```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '[.[] | select(.user.login == "{USERNAME}") | .submitted_at] | map(select(startswith("{TARGET_DATE}")))'
```

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments --jq '[.[] | select(.user.login == "{USERNAME}") | .created_at] | map(select(startswith("{TARGET_DATE}")))'
```

When `LAST_UPDATED` is **set** (incremental run):
```bash
gh api repos/{owner}/{repo}/pulls/{number}/reviews --jq '[.[] | select(.user.login == "{USERNAME}") | .submitted_at] | map(select(. > "{LAST_UPDATED}"))'
```

```bash
gh api repos/{owner}/{repo}/issues/{number}/comments --jq '[.[] | select(.user.login == "{USERNAME}") | .created_at] | map(select(. > "{LAST_UPDATED}"))'
```

- If **either** query returns a non-empty array, the PR had activity in the time window — include it
- If **both** return empty arrays, the user's activity was before the time window — **exclude** this PR
- Classify included PRs as `"Reviewed"` if the reviews query matched, otherwise `"Commented on"`

Then consolidate ALL verified non-authored PRs into **one task**:

1. **jira_ticket**: `"Reviewing Pull Requests"`
2. **descriptions**: One entry per PR, format: `"Reviewed <PR URL>"` or `"Commented on <PR URL>"`
   - If both reviewed AND commented, just use `"Reviewed <PR URL>"` (review implies comments)
   - **Sort order:** All `"Reviewed"` entries must come before all `"Commented on"` entries
3. **status**: `"completed"`
4. **github_pr**: `""` (empty, since there are multiple PRs)
5. **Build task object**:
   ```yaml
   - jira_ticket: "Reviewing Pull Requests"
     descriptions:
       - "Reviewed https://github.com/openshift/hypershift/pull/7835"
       - "Reviewed https://github.com/openshift/enhancements/pull/1945"
       - "Commented on https://github.com/openshift/hypershift/pull/7810"
     status: "completed"
     upnext_description: ""
     github_pr: ""
     blocker: ""
   ```

### Phase 4: Group Authored PRs by JIRA Ticket

For **authored PRs only**, if multiple share the same JIRA ticket (non-empty), merge them into a single task:
- Combine all descriptions into one `descriptions` array
- Use the first PR's URL as `github_pr`
- Use the "most active" status: if any PR is `"in progress"`, use that; if all completed, use `"completed"`

Authored PRs with empty JIRA tickets remain as separate tasks.

### Phase 5: Merge with Existing Worklog

1. **Read** the existing worklog.yaml file
2. **Check** if `TARGET_DATE` already has an entry:
   - If yes: collect all existing `github_pr` URLs for that date
   - **Same-day merge detection:** For each authored PR that is now merged/closed, check if an existing entry **for `TARGET_DATE`** has the same `github_pr` URL and `status: "in progress"`. If found, update that entry **in-place**: set `status: "completed"`, `upnext_description: ""`, and append `"PR merged"` to the `descriptions` array. Do NOT create a duplicate entry.
   - For remaining authored PR tasks: skip any whose `github_pr` already appears in existing entries **for that date** (and was not just updated by same-day merge detection above)
   - **Merged-on-different-day detection:** For each authored PR that is now merged/closed and was NOT already handled by same-day merge detection, perform two checks:
     1. **Match by `github_pr` URL:** Scan ALL dates in the worklog (not just `TARGET_DATE`) for an existing entry with the same `github_pr` URL and `status: "in progress"`. If found, the PR was previously logged as in-progress on an earlier date and has since merged — create a **new** completed entry for `TARGET_DATE` with description `"Merged PR: <title without JIRA prefix>"`, `status: "completed"`, and `upnext_description: ""`. Do NOT modify the earlier date's entry.
     2. **Match by `jira_ticket`:** If the URL match above did not find anything AND the merged PR has a non-empty JIRA ticket, scan ALL dates in the worklog for an existing entry with the same `jira_ticket` value and `status: "in progress"`. This catches cases where multiple PRs were grouped under one JIRA ticket but the `github_pr` field only stored one PR's URL. If found, create a **new** completed entry for `TARGET_DATE` with description `"Merged PR: <title without JIRA prefix>"`, `status: "completed"`, and `upnext_description: ""`. Do NOT modify the earlier date's entry.
   - For the consolidated review task: check if a `"Reviewing Pull Requests"` task already exists for that date. If so, check which PR URLs are already listed in its descriptions. Append only new descriptions (for PRs not already listed) to the existing task's `descriptions` array, then re-sort the full descriptions array so all `"Reviewed"` entries come before all `"Commented on"` entries. If no new PRs to add, skip.
   - Append only genuinely new authored tasks to the existing `tasks` array
   - If no new tasks to add, report "No new PR activity to add" and stop
   - If no entry for date: create new day entry:
     ```yaml
     "YYYY-MM-DD":
       work_log:
         - start_time: "08:00"
           end_time: ""
       tasks: [...]
     ```

### Phase 6: Preview and Write

1. **Display** the generated/new tasks to the user in YAML format
2. **Show summary**: "Found X PRs, generating Y new tasks (Z already in worklog)"
3. If incremental run, note: "Incremental run (since {LAST_UPDATED})"
4. If `--dry-run`: stop here
5. Otherwise, **ask the user to confirm** before writing
6. **Write** the updated worklog.yaml, preserving:
   - The new date entry at the TOP of the file (after the `---` line)
   - All existing entries below, unchanged
   - Exact YAML formatting matching existing entries (2-space indent, quoted strings for dates and values)
7. **Update `last_updated` timestamp:** After successfully writing tasks, set the `last_updated` field on the `TARGET_DATE` entry to the current UTC time in ISO 8601 format. Get the timestamp by running `date -u +%Y-%m-%dT%H:%M:%SZ`. Write it as the first field under the date key, before `work_log`:
   ```yaml
   "2026-04-02":
     last_updated: "2026-04-02T15:22:00Z"
     work_log:
       ...
   ```
   If `last_updated` already exists for this date, replace it with the new timestamp.

### YAML Formatting Rules

Match the existing worklog.yaml style exactly:
- Date keys are quoted: `"2026-03-03":`
- All string values are quoted: `"in progress"`, `"CNTRLPLANE-1985"`
- Empty strings are quoted: `""`
- Use `descriptions` (plural, array) not `description` (singular)
- 2-space indentation throughout
- List items use `- ` prefix with appropriate indentation
- `last_updated` is placed as the first field under the date key, before `work_log`

## Example Output

```yaml
"2026-03-03":
  last_updated: "2026-03-03T17:45:00Z"
  work_log:
    - start_time: "08:00"
      end_time: ""
  tasks:
    - jira_ticket: "CNTRLPLANE-1985"
      descriptions:
        - "Addressed Cesar's review comments on private topology enhancement"
        - "Updated API field naming per Alberto's feedback"
      status: "in progress"
      upnext_description: "Get PR reviewed and merged"
      github_pr: "https://github.com/openshift/enhancements/pull/1949"
      blocker: ""
    - jira_ticket: "OCPBUGS-74495"
      descriptions:
        - "Fixed build error in legacy storage client and added unit tests"
      status: "in progress"
      upnext_description: "Get PR reviewed and merged"
      github_pr: "https://github.com/openshift/cluster-image-registry-operator/pull/1287"
      blocker: ""
    - jira_ticket: "Reviewing Pull Requests"
      descriptions:
        - "Reviewed https://github.com/openshift/hypershift/pull/7835"
        - "Reviewed https://github.com/openshift/enhancements/pull/1945"
        - "Commented on https://github.com/openshift/hypershift/pull/7810"
      status: "completed"
      upnext_description: ""
      github_pr: ""
      blocker: ""
```
