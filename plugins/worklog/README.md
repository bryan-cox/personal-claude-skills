# Worklog Skills

Skills for tracking daily work activity and generating status reports.

## Skills

### `/update-worklog`

Queries GitHub for all PR activity (authored, reviewed, commented) on a given date and generates worklog.yaml task entries with contextual descriptions, auto-detected JIRA tickets, and inferred status. Supports incremental updates via `last_updated` timestamps.

### `/status-update`

Generates an HTML work report, commits a scrum status markdown file to a git repo, presents a dolphin-blog-style Slack summary, and posts status comments to JIRA tickets for the current biweekly reporting period. Automatically calculates the start date based on a Tuesday/Thursday cycle. Supports `--scrum-repo PATH` to override the default scrum status repo (`~/bryan-cox/scrum-status`).

## Prerequisites

- GitHub CLI (`gh`) must be installed and authenticated
- A worklog.yaml file (default: `~/worklog/worklog.yaml`)

### Additional prerequisites for `/status-update`

The `/status-update` skill depends on the [taskledger](https://github.com/bryan-cox/taskledger) plugin, which must be installed separately. It invokes `/taskledger:html-report` and `/taskledger:update-jira` to generate reports and post JIRA comments.

- [TaskLedger](https://github.com/bryan-cox/taskledger) binary built at `~/bryan-cox/taskledger/bin/taskledger`
- Atlassian JIRA MCP server configured for posting status comments
