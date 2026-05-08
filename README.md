# personal-claude-skills

A place for me to share personal Claude Code skills I use on a daily basis that might help others as well but I don't want to merge them into a formal repo just yet.

## Installation

1. Open Claude Code and run `/plugin`
2. Select **Add marketplace**
3. Enter the repository URL: `https://github.com/bryan-cox/personal-claude-skills`
4. Select **Install plugin**
5. Choose the plugin you want to install

## Available Plugins

### behavior-driven-testing

Guides writing of behavior-driven Go unit tests that prioritize testing meaningful behaviors over chasing code coverage.

**What it does:**
- Enforces Gherkin-style test naming: `"When <precondition>, it should <expected behavior>"`
- Promotes gomega assertions with expressive matchers
- Guides table-driven test structure (idiomatic Go)
- Covers fake clients, mocking patterns, and envtest guidance for Kubernetes API testing
- Encourages testing behaviors, not implementation details

### obsidian-vault

Provides vault structure, naming conventions, and the canonical daily work log format for an Obsidian vault at `~/Red Hat/`.

**Skills included:**
- `/obsidian-vault` — Reference skill for vault folder structure, note naming, linking conventions, and search/create workflows. Documents the daily log format used by the worklog plugin (`Work log/YYYY/MM/YYYY-MM-DD.md`).

**Related:** The [daily-log-format.md](plugins/obsidian-vault/skills/obsidian-vault/daily-log-format.md) file defines the canonical schema for daily work log notes.

---

### worklog

Populate Obsidian daily notes from GitHub PR activity and generate biweekly status reports with JIRA updates.

**Skills included:**
- `/update-worklog` — Queries GitHub for all PR activity (authored, reviewed, commented) on a given date and writes structured entries to the Obsidian daily note (`~/Red Hat/Work log/YYYY/MM/YYYY-MM-DD.md`) by default. Supports incremental updates via `last_updated` timestamps. Pass `--file PATH` to write to a worklog.yaml instead.
- `/status-update` — Generates an HTML work report and posts status comments to JIRA tickets for the current biweekly reporting period (Tuesday/Thursday cycle). Reads from Obsidian daily notes by default; pass `--file PATH` to use a worklog.yaml instead.

**Prerequisites:**
- GitHub CLI (`gh`) installed and authenticated
- Obsidian vault at `~/Red Hat/` with `Work log/` folder (see [obsidian-vault](#obsidian-vault) plugin)
- `/status-update` requires the [taskledger](https://github.com/bryan-cox/taskledger) plugin (invokes `/taskledger:html-report` and `/taskledger:update-jira`)
- Atlassian JIRA MCP server for posting status comments

### quarterly-connection

Generate Red Hat quarterly connection self-evaluations by analyzing worklog data, Jira tickets, GitHub PRs, and code reviews.

**Skills included:**
- `/quarterly-connection` — Interactively gathers your quarterly goals, self-evaluation questions, reward zone awards, and work history, then uses parallel agents to analyze your worklog.yaml, enrich Jira tickets, and summarize GitHub activity. Produces a well-organized markdown self-evaluation with work mapped to themes, high-priority items highlighted, and unanswerable questions flagged for your input.
- `/verify-qc` — Fact-checks a quarterly connection document by verifying Jira ticket ownership, PR merge status, numerical claims, and GitHub contribution links against real data. Reports errors, warnings, and unverifiable claims.

**Prerequisites:**
- Obsidian daily notes or worklog.yaml (produced by the [worklog](#worklog) plugin's `/update-worklog` skill)
- GitHub CLI (`gh`) installed and authenticated
- Atlassian JIRA MCP server (for enriching Jira ticket details)

### github-actions-expert

Expert guidance for writing, reviewing, debugging, and securing GitHub Actions workflows. Specializes in self-hosted ARM runners (ARC), Prow coexistence, reusable workflows, and OpenShift/HyperShift CI patterns.

**What it does:**
- Guides workflow authoring with correct runner labels, timeouts, permissions, and skip logic
- Security hardening: action pinning (SHA), least-privilege permissions, injection prevention, supply chain review
- Self-hosted runner expertise: ARC configuration, ARM architecture considerations, ephemeral runners, network policies
- Prow coexistence: clear separation of concerns between GHA (fast checks) and Prow (E2E, merge queue, chatops)
- Debugging: check name mismatches, trigger issues, runner troubleshooting
- Reusable workflows and composite actions patterns

### jira-pointer

Assign story points to Jira issues using the GCP HCP pointing rubric, recursively traversing feature/epic hierarchies.

**What it does:**
- Given a Feature or Epic, recursively walks the hierarchy and points every unpointed issue
- Supports `--dry-run`, `--force`, and custom story points field overrides

### to-issues

Break a plan into independently-grabbable issues using vertical slices (tracer bullets), then publish them to the tracker of your choice.

**What it does:**
- Decomposes a plan into thin, end-to-end vertical slices (not horizontal layers)
- Labels each slice as HITL (needs human input) or AFK (agent-ready)
- Maps dependency/blocking relationships between slices
- Asks the user to review and iterate on the breakdown before publishing
- Creates issues in the user's chosen tracker: Jira, GitHub Issues, Beads, or any other tool

Based on [mattpocock/skills](https://github.com/mattpocock/skills).
