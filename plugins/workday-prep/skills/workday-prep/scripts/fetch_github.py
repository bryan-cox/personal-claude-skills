#!/usr/bin/env python3
"""Fetch GitHub PRs needing review and authored open PRs, extract Jira keys, output JSON."""

import json
import re
import subprocess
import sys
import time


def run_gh(args, attempts=2):
    """Run a gh query, returning parsed JSON, or None if it fails after retries.

    Returning None (rather than []) matters: an empty list is a legitimate
    result ("no PRs need review"), so a failed query must not look like one.
    """
    last_err = ""
    for attempt in range(1, attempts + 1):
        try:
            result = subprocess.run(
                ["gh"] + args,
                capture_output=True, text=True, timeout=90
            )
        except subprocess.TimeoutExpired:
            last_err = "timed out"
        else:
            if result.returncode == 0:
                try:
                    return json.loads(result.stdout)
                except json.JSONDecodeError:
                    last_err = "unparseable JSON"
            else:
                last_err = result.stderr.strip()
        if attempt < attempts:
            time.sleep(3)
    print(f"Error: gh {' '.join(args[:4])}... failed: {last_err}", file=sys.stderr)
    return None


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

    approved_prs = run_gh([
        "search", "prs",
        "--reviewed-by=@me", "--review=approved", "--state=open",
        "--json", "url", "--limit", "200"
    ])

    authored_prs = run_gh([
        "search", "prs",
        "--author=@me", "--state=open",
        "--json", fields, "--limit", "200"
    ])

    # Never emit a partial file: a failed query would otherwise show up as an
    # empty review queue, which is indistinguishable from a genuinely quiet day.
    failed = [name for name, value in (
        ("review-requested", review_prs),
        ("approved", approved_prs),
        ("authored", authored_prs),
    ) if value is None]
    if failed:
        print(f"Error: GitHub query failed ({', '.join(failed)}); no output written. Retry.",
              file=sys.stderr)
        sys.exit(1)

    approved_urls = {pr.get("url", "") for pr in approved_prs}

    results = []
    seen = set()

    for pr in review_prs:
        if pr.get("url", "") in approved_urls:
            continue
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
    n_filtered = len(approved_urls & {pr.get("url", "") for pr in review_prs})
    print(f"\nFetched {len(review_prs)} review requests ({n_filtered} already approved, filtered out), {len(authored_prs)} authored PRs ({len(results)} unique)", file=sys.stderr)


if __name__ == "__main__":
    main()
