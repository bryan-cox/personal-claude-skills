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
from concurrent.futures import ThreadPoolExecutor, as_completed

CI_COMMAND_RE = re.compile(
    r"^\s*/(retest|test\s|override\s|pj-rehearse|pipeline\s|verified\s|close\b|refresh\b|cc\s|uncc\s|assign\s|unassign\s|remove-lifecycle\s|lifecycle\s|priority\s|kind\s|area\s|sig\s|wip\b|hold\b|unhold\b|cherry-pick\s|label\s|remove-label\s)",
    re.IGNORECASE,
)


def gh_api(path: str, jq_filter: str) -> str:
    result = subprocess.run(
        ["gh", "api", path, "--jq", jq_filter],
        capture_output=True, text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else "[]"


def get_username() -> str:
    result = subprocess.run(
        ["gh", "api", "user", "--jq", ".login"],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def date_filter(field: str, date: str, since: str) -> str:
    if since:
        return f'. > "{since}" and startswith("{date}")'
    return f'startswith("{date}")'


def fetch_authored_activity(pr: dict, date: str, since: str, username: str) -> dict:
    repo = pr["repo"]
    num = pr["number"]

    commits_jq = f'[.[] | select(.commit.author.date | {date_filter(".", date, since)}) | .commit.message]'
    reviews_jq = f'[.[] | select(.submitted_at | {date_filter(".", date, since)}) | {{user: .user.login, state: .state}}]'
    comments_jq = (
        f'[.[] | select(.user.login == "{username}") '
        f'| select(.created_at | {date_filter(".", date, since)}) '
        f'| {{user: .user.login, body: .body}}]'
    )

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_commits = pool.submit(gh_api, f"repos/{repo}/pulls/{num}/commits", commits_jq)
        f_reviews = pool.submit(gh_api, f"repos/{repo}/pulls/{num}/reviews", reviews_jq)
        f_comments = pool.submit(gh_api, f"repos/{repo}/issues/{num}/comments", comments_jq)

    commits = json.loads(f_commits.result() or "[]")
    reviews = json.loads(f_reviews.result() or "[]")
    comments_raw = json.loads(f_comments.result() or "[]")

    comments = [c for c in comments_raw if not CI_COMMAND_RE.match(c.get("body", ""))]

    return {"commits": commits, "reviews": reviews, "comments": comments}


def is_terminal(state: str) -> bool:
    return state.lower() in ("merged", "closed")


def generate_descriptions(pr: dict, activity: dict) -> list[str]:
    descs = []
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
    if pr["state"].lower() == "merged":
        descs.append("PR merged")
    return descs[:3] if descs else []


def infer_status(pr: dict) -> str:
    return "completed" if is_terminal(pr["state"]) else "in progress"


def infer_upnext(pr: dict) -> str:
    if is_terminal(pr["state"]):
        return ""
    if pr.get("isDraft"):
        return "Finish implementation, dev test, and mark the PR ready for review"
    return "Get PR reviewed and merged"


def verify_review_activity(pr: dict, date: str, since: str, username: str) -> str | None:
    repo = pr["repo"]
    num = pr["number"]
    filt = date_filter(".", date, since)

    reviews_jq = f'[.[] | select(.user.login == "{username}") | .submitted_at] | map(select({filt}))'
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
    args = parser.parse_args()

    data = json.load(sys.stdin)
    since = data.get("since", args.since)
    prs = data["prs"]

    username = get_username()

    authored = [p for p in prs if "authored" in p["sources"]]
    non_authored = [p for p in prs if "authored" not in p["sources"]]

    authored_tasks = []
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {pool.submit(fetch_authored_activity, pr, args.date, since, username): pr for pr in authored}
        for future in as_completed(futures):
            pr = futures[future]
            activity = future.result()
            has_activity = activity["commits"] or activity["reviews"] or activity["comments"]

            if not has_activity and not is_terminal(pr["state"]):
                continue

            descs = generate_descriptions(pr, activity) if has_activity else []
            if is_terminal(pr["state"]) and not descs:
                descs = ["PR merged"] if pr["state"].lower() == "merged" else ["PR closed"]

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
        status = "in progress" if any(t["status"] == "in progress" for t in tasks) else "completed"
        upnext = next((t["upnext_description"] for t in tasks if t["upnext_description"]), "")
        grouped_tasks.append({
            "jira_ticket": jira,
            "title": tasks[0]["title"],
            "descriptions": combined_descs,
            "status": status,
            "upnext_description": upnext,
            "github_pr": tasks[0]["github_pr"],
            "blocker": "",
        })
    grouped_tasks.extend(ungrouped)

    review_task = None
    if non_authored:
        review_descs = []
        with ThreadPoolExecutor(max_workers=5) as pool:
            futures = {pool.submit(verify_review_activity, pr, args.date, since, username): pr for pr in non_authored}
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
