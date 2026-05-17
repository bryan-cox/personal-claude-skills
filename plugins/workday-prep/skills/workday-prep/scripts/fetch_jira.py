#!/usr/bin/env python3
"""Fetch unresolved Jira issues assigned to current user via acli, output JSON."""

import json
import subprocess
import sys


def run_acli(jql, fields="key,summary,status,priority,labels,updated", limit=200):
    cmd = [
        "acli", "jira", "workitem", "search",
        "--jql", jql,
        "--fields", fields,
        "--json",
        "--limit", str(limit),
        "--paginate",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        if "auth" in result.stderr.lower() or "login" in result.stderr.lower():
            print("Error: Not authenticated. Run 'acli jira auth login --web' first.", file=sys.stderr)
            sys.exit(1)
        print(f"Warning: acli search failed: {result.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse acli output", file=sys.stderr)
        return []


def normalize_priority(priority_str):
    """Map Jira priority strings to standard names."""
    if not priority_str:
        return "Normal"
    p = priority_str.strip().lower()
    mapping = {
        "blocker": "Blocker",
        "critical": "Critical",
        "major": "Major",
        "normal": "Normal",
        "minor": "Minor",
        "trivial": "Minor",
        "highest": "Blocker",
        "high": "Critical",
        "medium": "Normal",
        "low": "Minor",
        "lowest": "Minor",
    }
    return mapping.get(p, "Normal")


def main():
    jql = "assignee = currentUser() AND resolution = Unresolved ORDER BY priority ASC"
    issues = run_acli(jql)

    results = []
    for issue in issues:
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

        results.append({
            "key": key,
            "summary": summary,
            "status": status_raw,
            "priority": normalize_priority(priority_raw),
            "priority_raw": priority_raw,
        })

    json.dump(results, sys.stdout, indent=2)
    print(f"\nFetched {len(results)} unresolved Jira issues", file=sys.stderr)


if __name__ == "__main__":
    main()
