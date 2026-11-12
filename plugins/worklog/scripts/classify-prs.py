#!/usr/bin/env python3
"""Classify fetched PRs into authored tasks and a consolidated review task.

Reads JSON from stdin (output of fetch-prs.py). For authored PRs, fetches
commits/reviews/comments to verify activity and generate descriptions.
Groups authored PRs by JIRA ticket. Outputs structured task JSON to stdout.

Usage:
    python3 fetch-prs.py --date 2026-05-26 | python3 classify-prs.py --date 2026-05-26
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

from worklog_window import ActivityWindow, DEFAULT_TIMEZONE

CI_COMMAND_RE = re.compile(
    r"^\s*/(retest|test\s|override\s|pj-rehearse|pipeline\s|verified\s|close\b|refresh\b|cc\s|uncc\s|assign\s|unassign\s|remove-lifecycle\s|lifecycle\s|priority\s|kind\s|area\s|sig\s|wip\b|hold\b|unhold\b|cherry-pick\s|label\s|remove-label\s)",
    re.IGNORECASE,
)


def gh_api(path: str, jq_filter: str) -> str:
    result = subprocess.run(
        ["gh", "api", path, "--paginate", "--jq", jq_filter],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode:
        if "403" not in result.stderr:
            raise RuntimeError("GitHub activity query failed: " + result.stderr.strip())
        values, url = [], "https://api.github.com/" + path
        while url:
            request = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "worklog-update"})
            with urllib.request.urlopen(request, timeout=40) as response:
                page = json.load(response)
                if isinstance(page, list):
                    values.extend(page)
                else:
                    values = page
                match = re.search(r'<([^>]+)>; rel="next"', response.headers.get("Link", ""))
                url = match.group(1) if match else None
        result = subprocess.run(["jq", "-c", jq_filter], input=json.dumps(values), capture_output=True, text=True, timeout=30)
        if result.returncode:
            raise RuntimeError("Public GitHub activity filtering failed")
    decoder, text, output = json.JSONDecoder(), result.stdout.strip(), []
    while text:
        page, offset = decoder.raw_decode(text)
        if not isinstance(page, list):
            raise ValueError("Expected a GitHub activity array")
        output.extend(page)
        text = text[offset:].lstrip()
    return json.dumps(output)


def get_username() -> str:
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True,
    )
    if result.returncode:
        raise RuntimeError("Could not resolve the GitHub user")
    return result.stdout.strip()


def date_filter(field: str, date: str, since: str, until: str = "", zone: str = DEFAULT_TIMEZONE) -> str:
    window = ActivityWindow.for_date(date, since, until, zone)
    operator = ">" if window.strict_start else ">="
    epoch = f"({field} | fromdateiso8601)"
    return f"{epoch} {operator} {window.since.timestamp()} and {epoch} <= {window.until.timestamp()}"


def fetch_authored_activity(pr: dict, date: str, since: str, username: str, until: str = "", zone: str = DEFAULT_TIMEZONE) -> dict:
    repo = pr["repo"]
    num = pr["number"]

    author_filt = date_filter(".", date, since, until, zone)
    committer_filt = date_filter(".", date, since, until, zone)
    commits_jq = (
        f'[.[] | select((.commit.author.date | {author_filt}) or (.commit.committer.date | {committer_filt}))'
        f' | .commit.message]'
    )
    reviews_jq = f'[.[] | select(.submitted_at != null) | select(.submitted_at | {date_filter(".", date, since, until, zone)}) | {{user: .user.login, state: .state}}]'
    comments_jq = (
        f'[.[] | select(.user.login == "{username}") '
        f'| select(.created_at | {date_filter(".", date, since, until, zone)}) '
        f'| {{user: .user.login, body: .body}}]'
    )
    lifecycle_jq = (
        '[{kind: "Opened PR", at: .created_at}, '
        '(if .merged_at then {kind: "PR merged", at: .merged_at} '
        'else {kind: "PR closed", at: .closed_at} end)] '
        '| map(select(.at != null) | select(.at | ' + author_filt + ') | .kind)'
    )

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_commits = pool.submit(gh_api, f"repos/{repo}/pulls/{num}/commits", commits_jq)
        f_reviews = pool.submit(gh_api, f"repos/{repo}/pulls/{num}/reviews", reviews_jq)
        f_comments = pool.submit(gh_api, f"repos/{repo}/issues/{num}/comments", comments_jq)
        f_lifecycle = pool.submit(gh_api, f"repos/{repo}/pulls/{num}", lifecycle_jq)

    commits = json.loads(f_commits.result() or "[]")
    reviews = json.loads(f_reviews.result() or "[]")
    comments_raw = json.loads(f_comments.result() or "[]")
    lifecycle = json.loads(f_lifecycle.result() or "[]")

    comments = [c for c in comments_raw if not CI_COMMAND_RE.match(c.get("body", ""))]

    return {"commits": commits, "reviews": reviews, "comments": comments, "lifecycle": lifecycle}


def is_terminal(state: str) -> bool:
    return state.lower() in ("merged", "closed")


def generate_descriptions(pr: dict, activity: dict) -> list[str]:
    descs = list(activity.get("lifecycle", []))
    for msg in activity["commits"]:
        first_line = msg.split("\n")[0].strip()
        if first_line:
            descs.append(f"Pushed: {first_line}")
    for rev in activity["reviews"]:
        user = rev["user"]
        state = rev["state"].replace("_", " ").lower()
        descs.append(f"Received {state} from {user}")
    for c in activity["comments"]:
        body = c.get("body", "")[:80].strip()
        if body:
            descs.append(f"Discussed: {body}")
    return descs[:3] if descs else []


def infer_status(pr: dict) -> str:
    return "completed" if is_terminal(pr["state"]) else "in progress"


def infer_upnext(pr: dict) -> str:
    if is_terminal(pr["state"]):
        return ""
    if pr.get("isDraft"):
        return "Finish implementation, dev test, and mark the PR ready for review"
    return "Get PR reviewed and merged"


def verify_review_activity(pr: dict, date: str, since: str, username: str, until: str = "", zone: str = DEFAULT_TIMEZONE) -> str | None:
    repo = pr["repo"]
    num = pr["number"]
    filt = date_filter(".", date, since, until, zone)

    reviews_jq = f'[.[] | select(.user.login == "{username}" and .submitted_at != null) | .submitted_at] | map(select({filt}))'
    comments_jq = f'[.[] | select(.user.login == "{username}") | .created_at] | map(select({filt}))'

    with ThreadPoolExecutor(max_workers=2) as pool:
        f_rev = pool.submit(gh_api, f"repos/{repo}/pulls/{num}/reviews", reviews_jq)
        f_com = pool.submit(gh_api, f"repos/{repo}/issues/{num}/comments", comments_jq)

    rev_dates = json.loads(f_rev.result() or "[]")
    com_dates = json.loads(f_com.result() or "[]")

    if rev_dates:
        return "Reviewed"
    if com_dates:
        return "Commented on"
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--since", default="", help="ISO 8601 timestamp for incremental")
    parser.add_argument("--until", default="", help="Fixed inclusive collection cutoff")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    args = parser.parse_args()

    data = json.load(sys.stdin)
    since = data.get("since", args.since)
    until = data.get("until") or args.until
    zone = data.get("timezone") or args.timezone
    prs = data["prs"]

    username = data.get("username") or get_username()

    authored = [p for p in prs if "authored" in p["sources"]]
    non_authored = [p for p in prs if "authored" not in p["sources"]]
    open_related = {}
    for pr in authored + data.get("open_authored_prs", []):
        if pr.get("jira") and pr.get("state", "").lower() == "open":
            open_related.setdefault(pr["jira"], set()).add(pr["url"])

    authored_tasks = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_authored_activity, pr, args.date, since, username, until, zone): pr for pr in authored}
        for future in as_completed(futures):
            pr = futures[future]
            activity = future.result()
            has_activity = any(activity.values())

            if not has_activity:
                continue

            descs = generate_descriptions(pr, activity) if has_activity else []
            if not descs:
                continue

            authored_tasks.append({
                "jira_ticket": pr["jira"],
                "title": pr["title"],
                "descriptions": descs,
                "status": infer_status(pr),
                "upnext_description": infer_upnext(pr),
                "github_pr": pr["url"],
                "blocker": "",
            })

    jira_groups: dict[str, list[dict]] = {}
    ungrouped = []
    for task in authored_tasks:
        jira = task["jira_ticket"]
        if jira:
            jira_groups.setdefault(jira, []).append(task)
        else:
            ungrouped.append(task)

    grouped_tasks = []
    for jira, tasks in jira_groups.items():
        combined_descs = []
        for t in tasks:
            combined_descs.extend(t["descriptions"])
        status = "in progress" if jira in open_related or any(t["status"] == "in progress" for t in tasks) else "completed"
        upnext = next((t["upnext_description"] for t in tasks if t["upnext_description"]), "")
        grouped_tasks.append({
            "jira_ticket": jira,
            "title": tasks[0]["title"],
            "descriptions": combined_descs,
            "status": status,
            "upnext_description": upnext,
            "github_pr": tasks[0]["github_pr"],
            "github_prs": list(dict.fromkeys([t["github_pr"] for t in tasks] + sorted(open_related.get(jira, [])))),
            "blocker": "",
        })
    grouped_tasks.extend(ungrouped)

    review_task = None
    if non_authored:
        review_descs = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(verify_review_activity, pr, args.date, since, username, until, zone): pr for pr in non_authored}
            for future in as_completed(futures):
                pr = futures[future]
                label = future.result()
                if label:
                    review_descs.append({"label": label, "url": pr["url"]})

        if review_descs:
            review_descs.sort(key=lambda d: (0 if d["label"] == "Reviewed" else 1, d["url"]))
            review_task = {
                "jira_ticket": "Reviewing Pull Requests",
                "descriptions": [f'{d["label"]} {d["url"]}' for d in review_descs],
                "status": "completed",
                "upnext_description": "",
                "github_pr": "",
                "blocker": "",
            }

    output = {"authored_tasks": grouped_tasks, "review_task": review_task}
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
