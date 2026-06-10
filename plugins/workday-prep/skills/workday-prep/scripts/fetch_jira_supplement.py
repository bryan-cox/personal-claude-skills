#!/usr/bin/env python3
"""Fetch Jira priorities for PR-referenced issues not in the user's assigned set."""

import json
import re
import sys

# Import shared utilities from fetch_jira
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from fetch_jira import load_jira_creds, login_acli, run_acli, normalize_priority

GH_FILE = "/tmp/workday-gh.json"
JIRA_FILE = "/tmp/workday-jira.json"


def main():
    with open(GH_FILE) as f:
        gh_prs = json.load(f)
    with open(JIRA_FILE) as f:
        jira_issues = json.load(f)

    existing_keys = {issue["key"] for issue in jira_issues}

    pr_jira_keys = set()
    for pr in gh_prs:
        key = pr.get("jira", "")
        if key and not re.match(r"^NO[-_]JIRA$", key, re.IGNORECASE):
            pr_jira_keys.add(key)

    missing_keys = pr_jira_keys - existing_keys
    if not missing_keys:
        print("No supplemental Jira issues to fetch.", file=sys.stderr)
        return

    print(f"Fetching {len(missing_keys)} supplemental Jira issues...", file=sys.stderr)

    keys_str = ", ".join(missing_keys)
    jql = f"key in ({keys_str})"
    raw_issues = run_acli(jql)

    supplemental = []
    for issue in raw_issues:
        key = issue.get("key", "")
        fields = issue.get("fields", issue)

        priority_raw = ""
        if isinstance(fields.get("priority"), dict):
            priority_raw = fields["priority"].get("name", "")
        elif isinstance(fields.get("priority"), str):
            priority_raw = fields["priority"]

        status_raw = ""
        if isinstance(fields.get("status"), dict):
            status_raw = fields["status"].get("name", "")
        elif isinstance(fields.get("status"), str):
            status_raw = fields["status"]

        summary = fields.get("summary", "")
        if isinstance(summary, dict):
            summary = summary.get("name", str(summary))

        supplemental.append({
            "key": key,
            "summary": summary,
            "status": status_raw,
            "priority": normalize_priority(priority_raw),
            "priority_raw": priority_raw,
            "_supplemental": True,
        })

    merged = jira_issues + supplemental
    with open(JIRA_FILE, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"Added {len(supplemental)} supplemental issues to {JIRA_FILE}", file=sys.stderr)


if __name__ == "__main__":
    main()
