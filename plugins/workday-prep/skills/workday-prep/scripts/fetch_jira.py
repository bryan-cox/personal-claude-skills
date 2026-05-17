#!/usr/bin/env python3
"""Fetch unresolved Jira issues assigned to current user via acli, output JSON."""

import json
import os
import subprocess
import sys
from pathlib import Path


def load_jira_creds():
    """Load Jira credentials from env vars or ~/.claude.json MCP config."""
    jira_url = os.environ.get("JIRA_URL")
    api_token = os.environ.get("JIRA_API_TOKEN")
    email = os.environ.get("JIRA_USERNAME") or os.environ.get("EMAIL")

    if all([jira_url, api_token, email]):
        return jira_url, email, api_token

    claude_json = Path.home() / ".claude.json"
    if claude_json.exists():
        try:
            data = json.loads(claude_json.read_text())
            env = data.get("mcpServers", {}).get("rh-jira", {}).get("env", {})
            jira_url = jira_url or env.get("JIRA_URL")
            api_token = api_token or env.get("JIRA_API_TOKEN")
            email = email or env.get("JIRA_USERNAME")
        except (json.JSONDecodeError, KeyError):
            pass

    if not all([jira_url, api_token, email]):
        missing = [v for v, val in [("JIRA_URL", jira_url), ("JIRA_API_TOKEN", api_token), ("JIRA_USERNAME", email)] if not val]
        print(f"Error: Missing Jira credentials: {', '.join(missing)}", file=sys.stderr)
        print("Set env vars or configure rh-jira in ~/.claude.json", file=sys.stderr)
        sys.exit(1)

    return jira_url, email, api_token


def login_acli():
    """Authenticate acli using credentials from env or ~/.claude.json."""
    jira_url, email, api_token = load_jira_creds()
    print(f"Authenticating with acli ({email} @ {jira_url})...", file=sys.stderr)
    result = subprocess.run(
        ["acli", "jira", "auth", "login", "--site", jira_url, "--email", email, "--token"],
        input=api_token,
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        print(f"Error: acli login failed: {result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    print("Login successful.", file=sys.stderr)


def run_acli(jql, fields="issuetype,key,summary,status,priority", limit=200):
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
            login_acli()
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                print(f"Error: acli search failed after login: {result.stderr.strip()}", file=sys.stderr)
                sys.exit(1)
        else:
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
