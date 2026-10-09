---
name: quarterly-connection
description: Use when writing a Red Hat quarterly connection self-evaluation, preparing a performance review, or when the user mentions "quarterly connection", "quarterly review", "self-evaluation", "quarterly self-assessment", or "performance review". Also trigger when the user wants to summarize a quarter's work from Obsidian daily work logs or a worklog.yaml file.
---

# Red Hat Quarterly Connection

Generate a comprehensive quarterly connection self-evaluation for a Red Hat software engineer. This document directly impacts the employee's performance rating and bonus, so thoroughness and accuracy are essential. The skill analyzes Obsidian daily work logs by default, with optional legacy worklog.yaml support, plus Jira tickets, GitHub PRs, and code reviews.

The questions change each quarter, so the skill asks the employee for the exact questions they need to answer and structures the output around those. Previous quarterly connections (if provided) inform style and tone — not structure.

## Workflow Overview

```
Gather Inputs (interactive)
    |
    v
Parallel Investigation (subagents, all opus model)
    |
    v
Synthesize & Organize by Theme
    |
    v
Draft Quarterly Connection (markdown)
    |
    v
Review with Employee & Refine
```

## Phase 1: Gather Inputs

Before any analysis, collect all required information from the employee. Ask for each of these **one at a time** to avoid overwhelming the user. Use the AskUserQuestion tool where appropriate, but for open-ended items just ask directly.

### 1.1 Work History Source

Ask: "What is the path to your Obsidian Work log folder or worklog.yaml file?"

Default to `~/Red Hat/Work log/` if the user confirms or doesn't specify. Obsidian notes use `YYYY/MM/YYYY-MM-DD.md`. Accept a vault root, `Work log` folder, year/month folder, an individual daily note, or a legacy `worklog.yaml` file. Use the date range to select the relevant daily notes.

### 1.2 Quarter Date Range

Ask: "What date range does this quarterly connection cover? (e.g., 2026-01-01 to 2026-03-31)"

Use this to filter Obsidian daily notes or legacy YAML entries to the relevant quarter.

### 1.3 Quarterly Goals

Ask: "What were your quarterly goals/priorities from last quarter? These will help organize your accomplishments into meaningful themes."

These are the priorities the employee set in their *previous* quarterly connection. They help map accomplishments to themes and demonstrate alignment. Work that doesn't fit any goal still gets included.

### 1.4 Quarterly Connection Questions

Ask: "What questions does the quarterly connection self-evaluation ask you to answer this quarter? Please paste them or list them."

The questions change each quarter. Do not assume or suggest specific questions — wait for what the employee provides. These questions become the top-level sections of the output document. Each question gets its own section with the question as a header.

### 1.5 Reward Zone Awards

Ask: "Did you receive or give any Reward Zone awards this quarter? If so, please share the details (who recognized you, what for, or who you recognized and why)."

Reward Zone awards are peer recognition at Red Hat. They provide strong evidence of impact and collaboration that managers value seeing in the QC, especially in the "Notable HOW accomplishments" section or as supporting evidence for themes.

### 1.6 Previous Quarterly Connections

Ask: "Do you have previous quarterly connections I can reference for tone and style? You can provide file paths, attach the documents, or paste the text."

If provided as a path, attachment, or pasted text, read them and use them as reference for:
- Writing style and tone
- Level of detail expected
- How accomplishments are grouped and framed
- Any recurring themes or long-running projects

If not provided, use the style guide in the "Document Format" section below.

### 1.7 Additional Context

Ask: "Is there anything else I should know before creating this report? This could include:
- Work not tracked in Jira or GitHub (mentoring, meetings, design discussions, oncall, interrupt catcher duties, etc.)
- Customer interactions or support
- Technical interviews conducted
- Production incidents assisted with
- Team onboarding or knowledge sharing sessions
- Anything else relevant to your performance this quarter"

This is the final catch-all. Everything the employee says here gets incorporated into the report.

## Phase 2: Parallel Investigation

After gathering all inputs, launch parallel subagents (model: opus) to investigate different data sources simultaneously. This phase is about extracting and enriching the raw data before organizing it.

### 2.1 Subagent: Work History Analysis

```
Analyze the selected work-history source at {work_history_path}.

Filter to entries between {start_date} and {end_date} inclusive.

If the source is Obsidian:
- Read daily notes matching `YYYY/MM/YYYY-MM-DD.md` within the date range. Select by the date in the filename and confirm it matches the `# Daily Log · YYYY-MM-DD` heading.
- In each note, parse task sections under `## Work`. Capture the task heading, Jira key, all `**PR:**` URLs, status, descriptions, `**Next:**` text, and explicit merge or close notes.
- Parse each `### Code Reviews` section. Separate `Reviewed` from `Commented on` URLs, then deduplicate URLs across dates while retaining both action types.
- Merge repeated Jira tasks and PR references across notes. Keep distinct descriptions and use the latest status recorded within the date range. A task marked `Completed` does not prove every linked PR merged; require an explicit merge note or verify against GitHub.
- Count distinct dated notes containing work, not repeated entries as extra days.

If the source is legacy `worklog.yaml`, extract the equivalent task and review fields from its entries.

For each task entry, extract:
- Date
- Jira ticket (if any)
- Descriptions (what was done)
- Status (completed, in progress)
- GitHub PR URL (if any)
- Blockers

Produce a structured summary:
1. Total distinct workdays logged
2. List of all unique Jira tickets worked on, with aggregated descriptions across all days
3. List of all GitHub PRs authored, with their final status
4. List of all PRs reviewed and commented on, grouped by action
5. Count of PRs explicitly noted as merged (exclude closed-without-merge) and unique PRs reviewed
6. Any blockers mentioned

Save the structured summary to a file.
```

### 2.2 Subagent: Jira Ticket Enrichment

Discover tickets from TWO sources and merge into a single deduplicated list:

**Source 1: Work history** — Extract all unique Jira ticket IDs from the selected Obsidian notes or legacy worklog.yaml entries.

**Source 2: Jira API** — Search Jira directly for tickets assigned to or resolved by the employee during the quarter:
- `assignee = {jira_username} AND resolved >= {start_date} AND resolved <= {end_date}`
- `assignee = {jira_username} AND status changed DURING ({start_date}, {end_date})`

Also search for tickets the employee reported (for aggregate stats only, not accomplishments):
- `reporter = {jira_username} AND created >= {start_date} AND created <= {end_date}`

This catches tickets not tracked in the selected work history (e.g., bugs fixed quickly without a note, tickets verified but not logged).

Use the Jira MCP tools if available, otherwise note that manual enrichment is needed.

```
For each unique Jira ticket from both sources:

Use the jira_get_issue MCP tool to fetch:
- Summary/title
- Priority (Blocker, Critical, Major, Minor, Trivial)
- Status
- Assignee
- Reporter
- Component
- Epic link (if any)
- Description summary (first 200 chars)

Ownership rules for including a ticket as an accomplishment:
- Include if the employee is/was the assignee
- Include if unassigned but the work history shows substantial authored work (PRs merged, etc.) — flag for employee to confirm
- Exclude if someone else is the assignee, UNLESS the work history shows the employee did significant work on it (e.g., backported a fix) — in that case, reframe the accomplishment to describe the employee's specific contribution, not the ticket itself

Reporter-only tickets (employee reported but someone else is assignee and no recorded work): count toward "tickets reported" aggregate stat but do NOT include as accomplishments.

Flag tickets with priority Blocker, Critical, or Major for special highlighting when Jira data confirms that priority. Mark unavailable Jira fields as unverified rather than inferring them from task status or PR titles.

Calculate aggregate Jira stats:
- Total tickets reported by the employee during the quarter
- Total tickets closed/resolved by the employee during the quarter
- Total tickets verified by the employee during the quarter

Group accomplishment tickets by:
1. Priority level
2. Epic/feature area (for theme grouping)

Save results to a file.
```

### 2.3 Subagent: GitHub PR Deep Dive

Discover PRs from TWO sources and merge into a single deduplicated list:

**Source 1: Work history** — Extract ALL unique repository URLs from `**PR:**` lines in Obsidian notes or `github_pr` fields in legacy worklog.yaml entries for the quarter. Do not hardcode or assume a list of repos.

**Source 2: GitHub API** — For every repo discovered in the work history, AND as a broad catch-all, query GitHub directly for all merged PRs by the employee during the quarter:
- Per repo: `gh pr list --repo {org}/{repo} --author {username} --state merged --search "merged:{start_date}..{end_date}" --limit 200`
- Broad search: `gh search prs --author {username} --merged --merged-at "{start_date}..{end_date}" --limit 1000` to discover repos not in the work history

This catches PRs not tracked in the work history (e.g., quick fixes, dependency bumps, or work in repos the employee forgot to log).

```
For each unique PR from both sources:
- PR title
- PR state (merged, open, closed)
- PR author (verify it matches the employee)
- Lines added/removed
- Number of review comments received
- Repository name
- Merge date (if merged)

Calculate aggregate stats (count only merged PRs, not closed-without-merge):
- Total PRs merged, grouped by every repository the employee contributed to
- Total lines changed (added + removed) across merged PRs
- Complete list of repos contributed to

Build GitHub Contributions links for each repository. Use is%3Amerged and merged%3A (not closed) to exclude PRs that were closed without merging:
https://github.com/{org}/{repo}/pulls?q=is%3Apr+is%3Amerged+author%3A{username}+merged%3A{start_date}..{end_date}

Save results to a file.
```

### 2.4 Subagent: Code Review Analysis

```
Analyze all code-review entries in the selected source between {start_date} and {end_date}. For Obsidian, use each daily note's `### Code Reviews` section. For legacy worklog.yaml, use entries with jira_ticket "Reviewing Pull Requests".

Extract every PR URL reviewed or commented on and preserve the action type.

Calculate:
- Total PRs reviewed
- Unique repositories reviewed
- Review frequency (reviews per week)

Save results to a file.
```

### 2.5 Subagent: Previous Quarterly Connection Analysis (if provided)

Only launch this if the employee provided previous quarterly connections.

```
Read the previous quarterly connection(s) from the paths, attachments, or pasted text supplied by the employee.

Analyze:
- Writing style and tone
- How accomplishments are grouped into themes
- Level of detail in each bullet point
- How Jira tickets are referenced
- How GitHub contributions are summarized
- What subsections or patterns appear within each question's response
- Any recurring themes or long-running projects that may continue into this quarter

Produce a style guide summary that can be used to match tone and format.
```

## Phase 3: Synthesize and Organize

Once all subagents complete, synthesize the results.

### 3.1 Group Work into Themes

Rather than organizing strictly by goal, group accomplishments into compelling narrative themes. Each theme should tell a story about a significant area of contribution. Look at the employee's quarterly goals and the work data to identify natural groupings.

Good themes are impact-oriented and specific:
- "Delivered self-managed Azure HostedCluster functionality to dev preview, enabling customer-0 adoption"
- "Resolved critical production bugs affecting ARO HCP reliability and performance"
- "Led AI tooling innovation through substantial contributions to the ai-helpers repository"

Bad themes are generic:
- "Bug fixes"
- "Code contributions"
- "Various improvements"

For each theme:
1. Write a bold header that summarizes the impact
2. List specific accomplishments as dash-prefixed bullets with Jira ticket IDs in parentheses
3. Each bullet should explain what was done AND why it mattered

### 3.2 Identify High-Impact Work

From the Jira enrichment data, identify and flag:
- **Blocker priority** tickets: These represent critical work that unblocked the team or organization
- **Critical priority** tickets: High-urgency work with significant impact
- **Major priority** tickets: Important work with broad reach

Weave these into the relevant themes rather than listing them separately. High-priority items should be near the top of their theme and their impact should be explicitly called out.

### 3.3 Build "Notable HOW Accomplishments"

This section is where the employee demonstrates leadership, collaboration, and engineering excellence beyond just "what" they delivered. Draw from:
- Worklog descriptions mentioning debugging, coordination, mentoring
- Interrupt catcher duties
- Cross-team collaboration
- Customer interactions
- Technical interviews
- Knowledge sharing / onboarding help
- Reward Zone awards (both given and received)
- Production incident support
- Process improvements
- Additional context the employee provided

### 3.4 Build GitHub Contributions Section

Aggregate PR counts by repository and generate search links:
```
GitHub Contributions:
- {Repo} Merged PRs: {count} - {search_url}
- {Repo} Merged PRs: {count} - {search_url}
```

### 3.5 Answer Each QC Question

For each question from section 1.4:
1. Determine whether the question can be answered from the gathered data (worklog, Jira, GitHub, additional context, reward zone awards)
2. If answerable: draft a thorough response using the synthesized data, organized with theme headers and dash-prefixed bullets where the content warrants it
3. If partially answerable: draft what you can and mark remaining gaps with `<!-- NEEDS INPUT: [specific guidance on what's needed] -->`
4. If the question is purely subjective/personal (e.g., about feelings, career aspirations, energy): mark with `<!-- NEEDS INPUT: This question requires your personal reflection. -->` and include any relevant data points from the quarter that might help the employee reflect (e.g., blockers encountered, rewarding themes, reward zone awards)

For forward-looking questions such as "What are your top priorities for this quarter?", use ongoing work only to suggest candidate priorities. Mark them for employee confirmation rather than presenting inferred priorities as commitments.

## Phase 4: Generate the Quarterly Connection Document

Produce the final document in markdown format matching the Red Hat QC style.

### Document Format

The document is structured around the questions the employee provided. Each question becomes a top-level section.

```markdown
# {Question 1 — short title}

**{The full question text}**

{Response content — organized with bold theme headers and dash-prefixed bullets for accomplishment-style questions, or bullet lists / prose for other question types}

---

# {Question 2 — short title}

**{The full question text}**

{Response content}

---

{Continue for each question}

---

## Sections Requiring Your Input

{List of questions/sections marked with <!-- NEEDS INPUT --> that the employee must fill in}
```

For questions that ask about accomplishments or work performed, use the theme-based grouping from Phase 3:

```markdown
**{Impact-oriented theme header}**
- {Accomplishment with Jira ticket ID in parentheses (TICKET-1234), explaining what was done and its impact}
- {Another accomplishment under this theme}

**{Another theme header}**
- {Accomplishments under this theme}

**Notable HOW accomplishments**
- {Leadership, collaboration, debugging, mentoring, etc.}
- {Reward Zone awards received or given}

GitHub Contributions:
- {Repo} Merged PRs: {count} - {search_url}
```

For questions that cannot be answered from data, provide the `<!-- NEEDS INPUT -->` marker with guidance on what the employee should write.

### Style Guide

If previous quarterly connections were provided, match their style. Otherwise, follow these defaults:

- **Bold headers** for accomplishment theme groups
- **Dash-prefixed bullets** (`- ` not `*` or numbered lists) for individual accomplishments
- **Jira ticket IDs inline in parentheses**: "Fixed the ExternalDNS deletion race condition (CNTRLPLANE-1857)"
- **Active voice, past tense** for accomplishments: "Implemented X enabling Y" not "X was implemented"
- **Impact-oriented framing**: every bullet should convey both what was done and why it mattered
- **Quantified metrics** where possible: PR counts, ticket counts, specific dates
- **Confident but not boastful tone** — let the work speak for itself

## Phase 5: Review and Refine

After generating the document:

1. Present the full markdown document to the employee
2. Call out the sections marked `<!-- NEEDS INPUT -->` and ask the employee to provide their input for those
3. Ask: "Would you like me to adjust anything? I can expand on specific accomplishments, reframe how something is presented, add context I might have missed, or adjust the tone."
4. Iterate on feedback until the employee is satisfied
5. Save the final document to a file path the employee specifies (default: `~/quarterly-connection-{quarter}-{year}.md`)
