#!/usr/bin/env python3
"""Merge the Phase 1 JSON files into the grouped workday-data.json the report reads."""

import json
import sys
import collections
from datetime import datetime, timezone

PRIORITY_ORDER = ["Blocker", "Critical", "Major", "Normal", "Minor", "Uncategorized"]

GH_PATH = "/tmp/workday-gh.json"
JIRA_PATH = "/tmp/workday-jira.json"
OUT_PATH = "/tmp/workday-data.json"


def main():
    gh = json.load(open(GH_PATH))
    jira = json.load(open(JIRA_PATH))

    groups = collections.defaultdict(list)
    item_by_key = {}

    # Seed with every Jira issue (assigned + supplemental) so issues without a
    # PR still appear in their priority group.
    for j in jira:
        priority = j.get("priority") or "Uncategorized"
        if priority not in PRIORITY_ORDER:
            priority = "Uncategorized"
        item = {
            "jira_key": j["key"],
            "jira_summary": j["summary"],
            "jira_status": j["status"],
            "prs": [],
        }
        item_by_key[j["key"]] = item
        groups[priority].append(item)

    unlinked = []
    for pr in gh:
        key = (pr.get("jira") or "").strip()
        record = {k: pr.get(k) for k in
                  ("url", "title", "action", "number", "repo", "isDraft", "updatedAt")}
        if key and key in item_by_key:
            item_by_key[key]["prs"].append(record)
        else:
            unlinked.append(record)

    out_groups = []
    for priority in PRIORITY_ORDER:
        items = groups.get(priority, [])
        if not items:
            continue
        # Issues with PRs first, then alphabetical by key.
        items.sort(key=lambda it: (0 if it["prs"] else 1, it["jira_key"]))
        out_groups.append({"priority": priority, "items": items})

    data = {
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "groups": out_groups,
        "unlinked_prs": sorted(
            unlinked, key=lambda x: (x["action"] != "review", -(x.get("number") or 0))),
        "jira_issues": [
            {"key": j["key"], "summary": j["summary"], "status": j["status"],
             "priority": j.get("priority") or "Uncategorized"}
            for j in jira if not j.get("_supplemental")
        ],
    }

    with open(OUT_PATH, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Wrote {OUT_PATH}: "
          + ", ".join(f"{g['priority']}={len(g['items'])} issues/"
                      f"{sum(len(i['prs']) for i in g['items'])} PRs" for g in out_groups)
          + f"; {len(unlinked)} unlinked PRs; {len(data['jira_issues'])} assigned issues")


if __name__ == "__main__":
    sys.exit(main())
