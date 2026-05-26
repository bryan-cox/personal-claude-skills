#!/usr/bin/env python3
"""Fetch GitHub PR activity (authored, reviewed, commented) for a date.

Runs three gh search queries in parallel, extracts JIRA tickets,
deduplicates by URL, and prints a JSON array to stdout.

Usage:
    python3 fetch-prs.py --date 2026-05-26 [--since 2026-05-26T15:00:00Z]
"""

import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

JIRA_RE = re.compile(r"[A-Z][A-Z0-9]+-\d+")

GH_FIELDS = "number,title,url,state,isDraft,repository,body,updatedAt"


def run_gh_search(flag: str, date: str) -> list[dict]:
    cmd = [
        "gh", "search", "prs",
        f"--{flag}=@me",
        f"--updated=>={date}",
        f"--json={GH_FIELDS}",
        "--limit=1000",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"warning: gh search --{flag} failed: {result.stderr.strip()}", file=sys.stderr)
        return []
    return json.loads(result.stdout) if result.stdout.strip() else []


def extract_jira(pr: dict) -> str:
    m = JIRA_RE.search(pr.get("title", ""))
    if not m:
        m = JIRA_RE.search(pr.get("body", "") or "")
    return m.group(0) if m else ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--since", default="", help="ISO 8601 timestamp for incremental runs")
    args = parser.parse_args()

    queries = ["author", "reviewed-by", "commenter"]
    source_labels = {"author": "authored", "reviewed-by": "reviewed", "commenter": "commented"}

    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {q: pool.submit(run_gh_search, q, args.date) for q in queries}
        results = {q: f.result() for q, f in futures.items()}

    merged: dict[str, dict] = {}
    for query, prs in results.items():
        label = source_labels[query]
        for pr in prs:
            url = pr["url"]
            if url not in merged:
                repo = pr.get("repository", {})
                merged[url] = {
                    "url": url,
                    "number": pr["number"],
                    "title": pr["title"],
                    "repo": repo.get("nameWithOwner", ""),
                    "state": pr["state"],
                    "isDraft": pr.get("isDraft", False),
                    "jira": extract_jira(pr),
                    "sources": [],
                    "updatedAt": pr.get("updatedAt", ""),
                }
            if label not in merged[url]["sources"]:
                merged[url]["sources"].append(label)

    output = list(merged.values())
    if args.since:
        print(json.dumps({"since": args.since, "prs": output}))
    else:
        print(json.dumps({"since": "", "prs": output}))


if __name__ == "__main__":
    main()
