# Daily Log Format

Daily log notes live at `Work log/YYYY/MM/YYYY-MM-DD.md` and follow this structure:

```markdown
# Daily Log · YYYY-MM-DD

*Last updated: YYYY-MM-DDTHH:MM:SSZ*

## 🕐 Hours
H:MM AM – H:MM PM

## 🦀 Work

### JIRA-123 · Task title here

**JIRA:** [JIRA-123](https://issues.redhat.com/browse/JIRA-123)
**PR:** [#1234](https://github.com/org/repo/pull/1234)
**Status:** In Progress

- Description bullet 1
- Description bullet 2

**Next:** Next step description

---

### Task title without JIRA

**PR:** [#1234](https://github.com/org/repo/pull/1234)
**Status:** Completed

- Description bullet

---

### Code Reviews

- Reviewed [PR #1234](https://github.com/org/repo/pull/1234)
- Commented on [PR #5678](https://github.com/org/repo/pull/5678)
```

Rules:

- `last_updated` is an ISO 8601 UTC timestamp updated each time the note is modified by a skill
- Hours use `H:MM AM – H:MM PM` format; set to `(not set)` if unknown
- Task sections: if the task has a JIRA ticket, the heading is `### JIRA-123 · Title` and includes a `**JIRA:**` line; if no JIRA, the heading is just `### Title` with no JIRA line
- `**Status:**` is either `In Progress` or `Completed`
- `**Next:**` line is omitted for completed tasks
- Tasks are separated by `---`
- Code Reviews section lists all reviewed/commented PRs with `Reviewed` entries sorted before `Commented on` entries
