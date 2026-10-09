# quarterly-connection

Generate comprehensive Red Hat quarterly connection self-evaluations for software engineers by analyzing Obsidian daily work logs by default, with optional legacy worklog.yaml support, plus Jira tickets, GitHub PRs, and code reviews.

**Skills included:**
- `/quarterly-connection` — Interactively gathers your quarterly goals, self-evaluation questions, and work history, then uses parallel agents to analyze Obsidian daily notes or a legacy worklog.yaml, enrich Jira tickets, and summarize GitHub activity. Produces a well-organized markdown self-evaluation with work mapped to themes, verified high-priority items highlighted, and unanswered questions flagged for your input.

**Prerequisites:**
- Obsidian daily work logs at `~/Red Hat/Work log/YYYY/MM/YYYY-MM-DD.md`, or an optional legacy worklog.yaml file
- GitHub CLI (`gh`) installed and authenticated
- Atlassian JIRA MCP server (for enriching Jira ticket details with priority, status, etc.)
