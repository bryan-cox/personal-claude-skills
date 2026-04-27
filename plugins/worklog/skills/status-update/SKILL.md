---
name: status-update
description: Use when generating biweekly work status reports and posting updates to Jira tickets, or when user says "status update" or "post status"
---

# Status Update

## Synopsis

```
/worklog:status-update [--obsidian]
```

## Arguments

- `--obsidian` _(optional)_: Read worklog data from Obsidian instead of a local YAML file. When passed, `--obsidian` is forwarded to both sub-skill invocations instead of `--file ~/worklog/worklog.yaml`.

## Overview

Generates an HTML work report and posts status comments to Jira tickets for the current reporting period. Automatically calculates the start date based on a Tuesday/Thursday biweekly cycle.

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
   - If `--obsidian` was passed:
     ```
     /taskledger:html-report --obsidian --start-date {calculated-start-date}
     ```
   - Otherwise:
     ```
     /taskledger:html-report --file ~/worklog/worklog.yaml --start-date {calculated-start-date}
     ```

3. **Invoke the Jira update skill**:
   - If `--obsidian` was passed:
     ```
     /taskledger:update-jira --obsidian --start-date {calculated-start-date}
     ```
   - Otherwise:
     ```
     /taskledger:update-jira --file ~/worklog/worklog.yaml --start-date {calculated-start-date}
     ```

4. **Report** the start date used and confirm both steps completed.
