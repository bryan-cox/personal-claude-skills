#!/usr/bin/env python3
"""Write classified PR tasks to an Obsidian daily note.

Reads task JSON from stdin (output of classify-prs.py). Handles merge
detection against existing notes, deduplication, and formatting.

Usage:
    python3 classify-prs.py ... | python3 write-obsidian.py --date 2026-05-26 [--dry-run]
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

WORKLOG_ROOT = Path.home() / "Red Hat" / "Work log"
JIRA_URL = "https://issues.redhat.com/browse"
LAST_UPDATED_RE = re.compile(r"^\*Last updated: (.+)\*$", re.MULTILINE)
CODE_REVIEWS_HEADER = "### Code Reviews"


def note_path(date: str) -> Path:
    y, m, _ = date.split("-")
    return WORKLOG_ROOT / y / m / f"{date}.md"


def read_existing(path: Path) -> str | None:
    if path.exists():
        return path.read_text()
    return None


def get_last_updated(content: str) -> str:
    m = LAST_UPDATED_RE.search(content)
    return m.group(1) if m else ""


def extract_existing_pr_urls(content: str) -> set[str]:
    return set(re.findall(r"https://github\.com/[^\s\)]+/pull/\d+", content))


def scan_all_notes_for_pr(url: str, exclude_date: str) -> bool:
    """Check if a PR URL appears in any note as an in-progress task."""
    for root, _, files in os.walk(WORKLOG_ROOT):
        for f in files:
            if not f.endswith(".md") or f.startswith(exclude_date):
                continue
            content = Path(root, f).read_text()
            if url in content and "In Progress" in content:
                return True
    return False


def scan_all_notes_for_jira(jira: str, exclude_date: str) -> bool:
    """Check if a JIRA ticket appears in any note as an in-progress task."""
    if not jira:
        return False
    for root, _, files in os.walk(WORKLOG_ROOT):
        for f in files:
            if not f.endswith(".md") or f.startswith(exclude_date):
                continue
            content = Path(root, f).read_text()
            if jira in content and "In Progress" in content:
                return True
    return False


def format_authored_task(task: dict) -> str:
    jira = task["jira_ticket"]
    pr_url = task["github_pr"]
    pr_num = pr_url.rstrip("/").split("/")[-1] if pr_url else ""
    status = "Completed" if task["status"] == "completed" else "In Progress"

    lines = []
    if jira:
        title = re.sub(r"^[A-Z][A-Z0-9]+-\d+[:\s]*", "", task.get("title", "")).strip()
        heading = f"{jira} · {title}" if title else jira
        lines.append(f"### {heading}")
        lines.append("")
        lines.append(f"**JIRA:** [{jira}]({JIRA_URL}/{jira})")
    else:
        lines.append(f"### {task.get('title', 'PR Work')}")
        lines.append("")

    if pr_url:
        lines.append(f"**PR:** [#{pr_num}]({pr_url})")
    lines.append(f"**Status:** {status}")
    lines.append("")

    for desc in task["descriptions"]:
        lines.append(f"- {desc}")

    if task["status"] != "completed" and task["upnext_description"]:
        lines.append("")
        lines.append(f"**Next:** {task['upnext_description']}")

    lines.append("")
    lines.append("---")
    return "\n".join(lines)


def parse_review_desc(desc: str) -> tuple[str, str]:
    """Parse 'Reviewed https://...' or 'Commented on https://...' into (label, url)."""
    m = re.match(r"^(Reviewed|Commented on)\s+(https://\S+)", desc)
    if m:
        return m.group(1), m.group(2)
    return desc, ""


def format_review_section(task: dict) -> str:
    lines = [CODE_REVIEWS_HEADER, ""]
    for desc in task["descriptions"]:
        label, url = parse_review_desc(desc)
        pr_num = url.rstrip("/").split("/")[-1] if url else ""
        lines.append(f"- {label} [PR #{pr_num}]({url})")
    return "\n".join(lines)


def create_new_note(date: str, timestamp: str) -> str:
    return f"""# Daily Log · {date}

*Last updated: {timestamp}*

## 🕐 Hours
(not set)

## 🦀 Work
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    data = json.load(sys.stdin)
    authored_tasks = data["authored_tasks"]
    review_task = data.get("review_task")

    path = note_path(args.date)
    existing = read_existing(path)
    existing_urls = extract_existing_pr_urls(existing) if existing else set()

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_sections = []
    skipped = 0
    updated_in_place = 0
    cross_date_merges = 0

    for task in authored_tasks:
        pr_url = task["github_pr"]

        if pr_url and pr_url in existing_urls:
            if task["status"] == "completed" and existing and "In Progress" in existing:
                # same-day merge detection handled by appending a note
                cross_date_merges += 1
            else:
                skipped += 1
                continue

        if task["status"] == "completed" and pr_url:
            if scan_all_notes_for_pr(pr_url, args.date):
                cross_date_merges += 1
            elif scan_all_notes_for_jira(task["jira_ticket"], args.date):
                cross_date_merges += 1

        new_sections.append(format_authored_task(task))

    review_section = None
    new_review_count = 0
    if review_task and review_task["descriptions"]:
        new_descs = [d for d in review_task["descriptions"] if parse_review_desc(d)[1] not in existing_urls]
        if new_descs:
            review_task["descriptions"] = new_descs
            new_review_count = len(new_descs)

            if existing and CODE_REVIEWS_HEADER in existing:
                existing_review_lines = []
                in_section = False
                for line in existing.split("\n"):
                    if line.strip() == CODE_REVIEWS_HEADER:
                        in_section = True
                        continue
                    if in_section:
                        if line.startswith("### ") or line.startswith("## "):
                            break
                        if line.startswith("- "):
                            existing_review_lines.append(line)

                new_formatted = []
                for d in new_descs:
                    label, url = parse_review_desc(d)
                    pr_num = url.rstrip("/").split("/")[-1] if url else ""
                    new_formatted.append(f"- {label} [PR #{pr_num}]({url})")

                all_lines = existing_review_lines + new_formatted
                reviewed = sorted([l for l in all_lines if "Reviewed" in l])
                commented = sorted([l for l in all_lines if "Commented" in l])
                review_section = CODE_REVIEWS_HEADER + "\n\n" + "\n".join(reviewed + commented)
            else:
                review_section = format_review_section(review_task)

    total_new = len(new_sections) + (1 if new_review_count else 0)
    if total_new == 0:
        print("No new PR activity to add.")
        return

    summary = f"Found {len(authored_tasks)} authored tasks, {new_review_count} reviews. "
    summary += f"Adding {len(new_sections)} new task sections. "
    if skipped:
        summary += f"Skipped {skipped} already logged. "
    if cross_date_merges:
        summary += f"Detected {cross_date_merges} cross-date merges. "
    print(summary)

    if args.dry_run:
        print("\n--- DRY RUN (would write): ---\n")
        for s in new_sections:
            print(s)
            print()
        if review_section:
            print(review_section)
        return

    if existing:
        content = LAST_UPDATED_RE.sub(f"*Last updated: {timestamp}*", existing)
        work_marker = "## 🦀 Work"
        if work_marker in content:
            idx = content.index(work_marker) + len(work_marker)
            insert = "\n" + "\n\n".join(new_sections)
            if review_section:
                if CODE_REVIEWS_HEADER in content:
                    old_start = content.index(CODE_REVIEWS_HEADER)
                    old_end = content.find("\n### ", old_start + 1)
                    if old_end == -1:
                        old_end = content.find("\n## ", old_start + 1)
                    if old_end == -1:
                        old_end = len(content)
                    content = content[:old_start] + review_section + content[old_end:]
                else:
                    insert += "\n\n" + review_section
            content = content[:idx] + insert + content[idx:]
        else:
            content += "\n## 🦀 Work\n" + "\n\n".join(new_sections)
            if review_section:
                content += "\n\n" + review_section
    else:
        content = create_new_note(args.date, timestamp)
        content += "\n".join(new_sections)
        if review_section:
            content += "\n\n" + review_section
        content += "\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    print(f"Wrote {path}")


if __name__ == "__main__":
    main()
