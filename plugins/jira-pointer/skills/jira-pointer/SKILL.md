---
name: jira-pointer
description: Assign story points to Jira issues using the GCP HCP pointing rubric. Recursively walks feature -> epic -> story/task hierarchies and points everything that isn't already pointed. Use this skill whenever the user wants to point, estimate, or size Jira issues, or mentions "point this feature/epic/story", "estimate story points", "size these tickets", or provides a Jira key and asks for pointing.
---

# Jira Pointer

Assign story points to Jira issues based on the GCP HCP team's pointing rubric. When given a Feature or Epic, recursively traverse the hierarchy and point every unpointed issue.

## Synopsis

```
/jira-pointer:jira-pointer <ISSUE-KEY> [--dry-run] [--force] [--field FIELD_ID]
```

- `ISSUE-KEY`: A Jira issue key (e.g., `OCPBUGS-123`, `HOSTEDCP-1234`)
- `--dry-run`: Show proposed points without writing anything
- `--force`: Re-point issues that already have points assigned
- `--field FIELD_ID`: Override the story points field (default: `customfield_10028` — "Story Points")

## Pointing Rubric

Use this scale to assess each issue based on its summary, description, acceptance criteria, and any linked context:

| Points | When to use |
|--------|-------------|
| **0** | Rarely used. Trivial task with stakeholder value but less risk/complexity than a 1-pointer. Example: Update a README link. |
| **1** | The smallest issue possible — everything scales from here. One-line code change, extremely simple task. No risk, very low effort, very low complexity. |
| **2** | Simple, well-understood change. Low risk, low complexity but slightly more effort than a 1. Some investigation into approach may be needed. |
| **3** | Doesn't have to be complex, but usually time consuming. Work is fairly straightforward. Minor risks may be present. |
| **5** | Requires investigation, design, discussions, collaboration. Can be time consuming or complex. Risks involved. |
| **8** | Big task. Requires investigation, design, discussions, collaboration. Solution is challenging. Risks expected. Design doc required. **Consider splitting into smaller stories.** |
| **13** | Should not be used. If an issue is this big, **it must be split into smaller stories.** |

When deciding points, read the issue's summary and description carefully. Assess each issue on its own merits — the same issue should receive the same score whether you encounter it as a standalone request or as part of a larger hierarchy traversal. Consider:
- How much investigation or design is needed?
- How many files/components will be touched?
- Are there dependencies or cross-team collaboration needed?
- What's the risk level — could this break something?
- Is this well-understood or exploratory?

## Workflow

### Step 1: Fetch the root issue

Use `jira_get_issue` to fetch the issue specified by the user. Include `*all` fields to get story points and issue type.

Determine the issue type:
- **Feature** — find all child Epics, then each Epic's child Stories/Tasks
- **Epic** — find all child Stories/Tasks
- **Story / Task / Bug / Sub-task** — point this single issue

### Step 2: Build the issue tree

For Features and Epics, use `jira_search` with JQL to find children:

- Children of a Feature: `"parent = <FEATURE-KEY>"`
- Children of an Epic: `"parent = <EPIC-KEY>"`

Paginate through all results (use `start_at` and `limit`). Collect every issue in the tree.

### Step 3: Filter to eligible issues

Skip any issue whose status category is **Done** (e.g., Closed, Resolved). There is no value in retroactively pointing completed work.

For the remaining issues, check `customfield_10028` (Story Points). If the field is `null`, `0`, or absent, the issue needs pointing. If `--force` is passed, include already-pointed issues too.

In the summary report, list skipped closed issues separately so the user knows they were seen but intentionally excluded.

### Step 4: Assess and propose points

For each unpointed issue, read its summary and description and assign a point value using the rubric above.

Build a proposal table showing:

```
| Issue Key    | Type  | Summary                           | Proposed Points | Rationale                        |
|--------------|-------|-----------------------------------|-----------------|----------------------------------|
| PROJ-101     | Story | Add health check endpoint         | 2               | Simple, well-understood change   |
| PROJ-102     | Task  | Design auth token rotation        | 5               | Requires investigation & design  |
| PROJ-103     | Story | Refactor metrics pipeline         | 8               | Big task, consider splitting     |
```

### Step 5: Flag large issues

For any issue assessed at **8 points**, add a warning: "Consider splitting into smaller stories."

For any issue assessed at **13 points**, add a strong warning: "This issue must be split into smaller stories. Pointing at 13 is not recommended."

Group these flagged issues separately at the top of your output so they're easy to spot.

### Step 6: Confirm with the user

Present the full proposal table to the user. Ask: "Does this look right? You can adjust any points before I write them."

Wait for the user to confirm or provide overrides.

If `--dry-run` was specified, stop here — do not write anything.

### Step 7: Write story points

For each confirmed issue, use `jira_update_issue` to set the story points:

```
jira_update_issue(
  issue_key="PROJ-101",
  fields='{"customfield_10028": 2}'
)
```

### Step 8: Summary report

After writing, present a final summary:

```
Pointed X issues:
- PROJ-101: 2 pts (Story — Add health check endpoint)
- PROJ-102: 5 pts (Task — Design auth token rotation)

Skipped Y issues (already pointed):
- PROJ-100: 3 pts (existing)

Skipped Z issues (closed):
- PROJ-099: Closed — not pointed

Flagged W issues for splitting:
- PROJ-103: 8 pts — consider splitting
```

Include total points assigned across the hierarchy.

## Error Handling

- If an issue key doesn't exist, report the error and stop.
- If the story points field is not available on the issue type, report which issues were skipped and why.
- If the hierarchy is large (50+ issues), process in batches and show progress updates.
