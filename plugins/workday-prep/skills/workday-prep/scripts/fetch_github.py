#!/usr/bin/env python3
"""Fetch GitHub PRs needing review and authored open PRs, extract Jira keys, output JSON."""

import json
import re
import subprocess
import sys


def run_gh(args):
    result = subprocess.run(
        ["gh"] + args,
        capture_output=True, text=True, timeout=60
    )
    if result.returncode != 0:
        print(f"Warning: gh {' '.join(args[:4])}... failed: {result.stderr.strip()}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def extract_jira(pr):
    for field in ("title", "body"):
        m = re.search(r"[A-Z][A-Z0-9]+-\d+", pr.get(field, "") or "")
        if m:
            return m.group(0)
    return ""


def main():
    fields = "number,title,url,state,isDraft,repository,updatedAt,body"

    review_prs = run_gh([
        "search", "prs",
        "--review-requested=@me", "--state=open",
        "--json", fields, "--limit", "200"
    ])

    authored_prs = run_gh([
        "search", "prs",
        "--author=@me", "--state=open",
        "--json", fields, "--limit", "200"
    ])

    results = []
    seen = set()

    for pr in review_prs:
        url = pr.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        repo = pr.get("repository", {})
        results.append({
            "url": url,
            "title": pr.get("title", ""),
            "number": pr.get("number", 0),
            "repo": repo.get("nameWithOwner", ""),
            "isDraft": pr.get("isDraft", False),
            "state": pr.get("state", ""),
            "updatedAt": pr.get("updatedAt", ""),
            "jira": extract_jira(pr),
            "action": "review",
        })

    for pr in authored_prs:
        url = pr.get("url", "")
        if url in seen:
            continue
        seen.add(url)
        repo = pr.get("repository", {})
        results.append({
            "url": url,
            "title": pr.get("title", ""),
            "number": pr.get("number", 0),
            "repo": repo.get("nameWithOwner", ""),
            "isDraft": pr.get("isDraft", False),
            "state": pr.get("state", ""),
            "updatedAt": pr.get("updatedAt", ""),
            "jira": extract_jira(pr),
            "action": "followup",
        })

    json.dump(results, sys.stdout, indent=2)
    print(f"\nFetched {len(review_prs)} review requests, {len(authored_prs)} authored PRs ({len(results)} unique)", file=sys.stderr)


if __name__ == "__main__":
    main()
