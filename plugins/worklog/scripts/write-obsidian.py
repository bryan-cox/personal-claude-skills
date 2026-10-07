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
JIRA_KEY_RE = re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b")
TASK_HEADING_RE = re.compile(r"^### (.+)$", re.MULTILINE)


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


def task_pr_urls(task: dict) -> list[str]:
    urls = []
    for url in [task.get("github_pr", ""), *(task.get("github_prs") or [])]:
        if url and url not in urls:
            urls.append(url)
    return urls


def task_descriptions(task: dict) -> list[str]:
    descriptions = []
    if task.get("description"):
        descriptions.append(task["description"])
    descriptions.extend(task.get("descriptions") or [])

    unique = []
    seen = set()
    for description in descriptions:
        description = str(description).strip()
        normalized = " ".join(description.split())
        if normalized and normalized not in seen:
            unique.append(description)
            seen.add(normalized)
    return unique


def coalesce_authored_tasks(tasks: list[dict]) -> list[dict]:
    """Combine GitHub and Jira tasks for the same issue into one work item."""
    result = []
    by_jira = {}

    for original in tasks:
        task = dict(original)
        jira = task.get("jira_ticket", "")
        match = JIRA_KEY_RE.search(str(jira)) if jira else None
        if not match:
            task["descriptions"] = task_descriptions(task)
            task.pop("description", None)
            result.append(task)
            continue

        ticket = match.group(0).upper()
        task["jira_ticket"] = ticket
        if ticket not in by_jira:
            task["descriptions"] = task_descriptions(task)
            task.pop("description", None)
            urls = task_pr_urls(task)
            task["github_prs"] = urls
            task["github_pr"] = urls[0] if urls else ""
            by_jira[ticket] = task
            result.append(task)
            continue

        combined = by_jira[ticket]
        descriptions = task_descriptions(combined)
        seen_descriptions = {" ".join(d.split()) for d in descriptions}
        for description in task_descriptions(task):
            normalized = " ".join(description.split())
            if normalized not in seen_descriptions:
                descriptions.append(description)
                seen_descriptions.add(normalized)
        combined["descriptions"] = descriptions
        combined.pop("description", None)

        urls = task_pr_urls(combined)
        for url in task_pr_urls(task):
            if url not in urls:
                urls.append(url)
        combined["github_prs"] = urls
        combined["github_pr"] = urls[0] if urls else ""

        statuses = {combined.get("status", ""), task.get("status", "")}
        if "in progress" in statuses or "not started" in statuses:
            combined["status"] = "in progress"
        elif "completed" in statuses:
            combined["status"] = "completed"
        if task.get("upnext_description"):
            combined["upnext_description"] = task["upnext_description"]
        if not combined.get("title") and task.get("title"):
            combined["title"] = task["title"]

    return result


def jira_key_in_task_block(block: str) -> str:
    jira_link = re.search(r"\*\*JIRA:\*\*.*?\[([A-Z][A-Z0-9]+-\d+)\]", block)
    if jira_link:
        return jira_link.group(1).upper()
    heading = re.search(r"(?m)^###\s+([A-Z][A-Z0-9]+-\d+)(?:\s|$)", block)
    return heading.group(1).upper() if heading else ""


def find_jira_task_section(content: str, jira_ticket: str) -> tuple[int, int, str] | None:
    work_marker = "## 🦀 Work"
    work_start = content.find(work_marker)
    if work_start == -1:
        return None

    body_start = work_start + len(work_marker)
    next_section = re.search(r"(?m)^## ", content[body_start:])
    body_end = body_start + next_section.start() if next_section else len(content)
    body = content[body_start:body_end]
    headings = list(TASK_HEADING_RE.finditer(body))

    for index, heading in enumerate(headings):
        if heading.group(1).strip() == "Code Reviews":
            break
        start = body_start + heading.start()
        end = body_start + (headings[index + 1].start() if index + 1 < len(headings) else len(body))
        block = content[start:end]
        if jira_key_in_task_block(block) == jira_ticket.upper():
            return start, end, block
    return None


def merge_jira_task_into_existing(content: str, task: dict) -> tuple[str, bool, bool, str]:
    """Merge new activity into an existing task section for the same Jira ticket.

    Returns the updated note, whether a matching section was found, whether it
    changed, and the merged section for dry-run previews.
    """
    ticket_match = JIRA_KEY_RE.search(str(task.get("jira_ticket", "")))
    if not ticket_match:
        return content, False, False, ""

    bounds = find_jira_task_section(content, ticket_match.group(0).upper())
    if bounds is None:
        return content, False, False, ""

    start, end, block = bounds
    lines = block.split("\n")
    existing_prs = extract_existing_pr_urls(block)
    new_prs = [url for url in task_pr_urls(task) if url not in existing_prs]
    new_descriptions = []
    existing_descriptions = {
        " ".join(line[2:].strip().split())
        for line in lines
        if line.startswith("- ")
    }
    seen_descriptions = set(existing_descriptions)
    for description in task_descriptions(task):
        normalized = " ".join(description.split())
        if normalized not in seen_descriptions:
            new_descriptions.append(description)
            seen_descriptions.add(normalized)

    if new_prs:
        status_index = next(
            (i for i, line in enumerate(lines) if line.startswith("**Status:**")),
            next((i for i, line in enumerate(lines) if line.startswith("**Next:**") or line.strip() == "---"), len(lines)),
        )
        pr_lines = [f"**PR:** [#{url.rstrip('/').split('/')[-1]}]({url})" for url in new_prs]
        lines[status_index:status_index] = pr_lines

    if new_descriptions:
        description_index = next(
            (i for i, line in enumerate(lines) if line.startswith("**Next:**") or line.strip() == "---"),
            len(lines),
        )
        lines[description_index:description_index] = [f"- {description}" for description in new_descriptions] + [""]

    desired_status = None
    if task.get("status") == "completed":
        desired_status = "Completed"
    elif task.get("status") in ("in progress", "not started"):
        desired_status = "In Progress"

    if desired_status:
        status_index = next((i for i, line in enumerate(lines) if line.startswith("**Status:**")), None)
        if status_index is not None:
            lines[status_index] = f"**Status:** {desired_status}"

    upnext = task.get("upnext_description", "").strip()
    next_indices = [i for i, line in enumerate(lines) if line.startswith("**Next:**")]
    if desired_status == "Completed":
        lines = [line for line in lines if not line.startswith("**Next:**")]
    elif upnext:
        next_line = f"**Next:** {upnext}"
        if next_indices:
            lines[next_indices[0]] = next_line
            for index in reversed(next_indices[1:]):
                del lines[index]
        else:
            separator_index = next((i for i, line in enumerate(lines) if line.strip() == "---"), len(lines))
            lines[separator_index:separator_index] = [next_line, ""]

    merged_block = "\n".join(lines)
    changed = merged_block != block
    if changed:
        content = content[:start] + merged_block + content[end:]
    return content, True, changed, merged_block


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
    jira = task.get("jira_ticket", "")
    pr_urls = task_pr_urls(task)
    status = "Completed" if task.get("status") == "completed" else "In Progress"

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

    for pr_url in pr_urls:
        pr_num = pr_url.rstrip("/").split("/")[-1]
        lines.append(f"**PR:** [#{pr_num}]({pr_url})")
    lines.append(f"**Status:** {status}")
    lines.append("")

    for desc in task_descriptions(task):
        lines.append(f"- {desc}")

    if task.get("status") != "completed" and task.get("upnext_description"):
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
    authored_tasks = coalesce_authored_tasks(data.get("authored_tasks", []))
    review_task = data.get("review_task")

    path = note_path(args.date)
    existing = read_existing(path)
    content = existing or ""

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    new_sections = []
    updated_sections = []
    pending_pr_urls = set()
    skipped = 0
    updated_in_place = 0
    cross_date_merges = 0

    for task in authored_tasks:
        jira_match = JIRA_KEY_RE.search(str(task.get("jira_ticket", "")))
        if jira_match:
            content, found, changed, merged_block = merge_jira_task_into_existing(
                content, task
            )
            if found:
                if changed:
                    updated_in_place += 1
                    updated_sections.append(merged_block)
                else:
                    skipped += 1
                continue

        pr_urls = task_pr_urls(task)
        existing_urls = extract_existing_pr_urls(content) | pending_pr_urls
        if any(pr_url in existing_urls for pr_url in pr_urls):
            skipped += 1
            continue

        if task.get("status") == "completed":
            found_cross_date_pr = any(
                scan_all_notes_for_pr(pr_url, args.date) for pr_url in pr_urls
            )
            if found_cross_date_pr or (
                jira_match and scan_all_notes_for_jira(jira_match.group(0), args.date)
            ):
                cross_date_merges += 1

        new_sections.append(format_authored_task(task))
        pending_pr_urls.update(pr_urls)

    existing_urls = extract_existing_pr_urls(content) | pending_pr_urls
    review_section = None
    new_review_count = 0
    if review_task and review_task.get("descriptions"):
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

    total_new = len(new_sections) + updated_in_place + (1 if new_review_count else 0)
    if total_new == 0:
        print("No new GitHub or Jira activity to add.")
        return

    summary = f"Found {len(authored_tasks)} authored/Jira task groups, {new_review_count} new reviews. "
    summary += f"Adding {len(new_sections)} task sections and merging {updated_in_place} existing sections. "
    if skipped:
        summary += f"Skipped {skipped} already logged. "
    if cross_date_merges:
        summary += f"Detected {cross_date_merges} cross-date merges. "
    print(summary)

    if args.dry_run:
        print("\n--- DRY RUN (would write): ---\n")
        for section in updated_sections:
            print("--- MERGED INTO EXISTING TASK ---")
            print(section)
            print()
        for s in new_sections:
            print(s)
            print()
        if review_section:
            print(review_section)
        return

    if existing:
        content = LAST_UPDATED_RE.sub(f"*Last updated: {timestamp}*", content)
        if f"*Last updated: {timestamp}*" not in content:
            heading_end = content.index("\n") + 1
            content = content[:heading_end] + f"\n*Last updated: {timestamp}*\n" + content[heading_end:]
        work_marker = "## 🦀 Work"
        if work_marker in content:
            idx = content.index(work_marker) + len(work_marker)
            insert = "\n" + "\n\n".join(new_sections) if new_sections else ""
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
