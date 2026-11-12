import importlib.util
import unittest
import sys
import tempfile
import io
import json
from contextlib import redirect_stdout
from unittest.mock import patch
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "write-obsidian.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("write_obsidian", SCRIPT)
write_obsidian = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(write_obsidian)


class CompletedWindowTests(unittest.TestCase):
    def test_empty_successful_scan_advances_only_to_its_cutoff_and_preserves_notes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);note=root/'2026/11/2026-11-12.md';note.parent.mkdir(parents=True)
            note.write_text('# Daily Log · 2026-11-12\n\n*Last updated: 2026-11-12T13:00:00Z*\n\n## 🕐 Hours\n7:00 AM to 3:30 PM\n\nMy manual notes stay here.\n')
            with patch.object(write_obsidian,'WORKLOG_ROOT',root), patch.object(sys,'argv',['writer','--date','2026-11-12','--last-updated','2026-11-12T17:00:00Z']), patch.object(sys,'stdin',io.StringIO(json.dumps({'authored_tasks':[],'review_task':None}))), redirect_stdout(io.StringIO()):
                write_obsidian.main()
            text=note.read_text()
            self.assertIn('*Last updated: 2026-11-12T17:00:00Z*',text)
            self.assertIn('My manual notes stay here.',text)
            self.assertIn('7:00 AM to 3:30 PM',text)

    def test_first_empty_scan_creates_the_new_daily_note_with_the_completed_cutoff(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with patch.object(write_obsidian,'WORKLOG_ROOT',root), patch.object(sys,'argv',['writer','--date','2026-11-13','--last-updated','2026-11-13T13:00:00Z']), patch.object(sys,'stdin',io.StringIO('{}')), redirect_stdout(io.StringIO()):
                write_obsidian.main()
            note=root/'2026/11/2026-11-13.md'
            self.assertTrue(note.is_file())
            self.assertIn('*Last updated: 2026-11-13T13:00:00Z*',note.read_text())


class MergeJiraTaskTests(unittest.TestCase):
    def setUp(self):
        self.note = """# Daily Log · 2026-10-07

*Last updated: 2026-10-07T10:00:00Z*

## 🦀 Work
### CNTRLPLANE-123 · Update test fixtures

**JIRA:** [CNTRLPLANE-123](https://issues.redhat.com/browse/CNTRLPLANE-123)
**PR:** [#42](https://github.com/example/project/pull/42)
**Status:** In Progress

- Refreshed the fixture baseline.

**Next:** Get PR reviewed and merged

---

### Code Reviews

- Reviewed [PR #43](https://github.com/example/project/pull/43)
"""

    def test_when_jira_activity_matches_an_existing_pr_task_it_should_merge_once(self):
        task = {
            "jira_ticket": "CNTRLPLANE-123",
            "descriptions": [
                "Refreshed the fixture baseline.",
                "Changed status from In Progress to Code Review.",
            ],
            "status": "in progress",
            "upnext_description": "Get PR reviewed and merged",
            "github_pr": "https://github.com/example/project/pull/42",
        }

        updated, found, changed, _ = write_obsidian.merge_jira_task_into_existing(self.note, task)

        self.assertTrue(found)
        self.assertTrue(changed)
        self.assertEqual(updated.count("### CNTRLPLANE-123"), 1)
        self.assertEqual(updated.count("- Refreshed the fixture baseline."), 1)
        self.assertEqual(updated.count("- Changed status from In Progress to Code Review."), 1)
        self.assertEqual(updated.count("**PR:**"), 1)
        self.assertIn("### Code Reviews", updated)

    def test_when_a_merged_task_has_a_new_pr_it_should_add_only_the_missing_pr_link(self):
        task = {
            "jira_ticket": "CNTRLPLANE-123",
            "descriptions": ["Added a second fix."],
            "status": "in progress",
            "github_prs": [
                "https://github.com/example/project/pull/42",
                "https://github.com/example/project/pull/44",
            ],
        }

        updated, found, changed, _ = write_obsidian.merge_jira_task_into_existing(self.note, task)

        self.assertTrue(found)
        self.assertTrue(changed)
        self.assertEqual(updated.count("**PR:**"), 2)
        self.assertEqual(updated.count("https://github.com/example/project/pull/42"), 1)
        self.assertEqual(updated.count("https://github.com/example/project/pull/44"), 1)

    def test_when_jira_activity_is_already_logged_it_should_not_duplicate_it(self):
        task = {
            "jira_ticket": "CNTRLPLANE-123",
            "descriptions": ["Refreshed the fixture baseline."],
            "status": "in progress",
            "upnext_description": "Get PR reviewed and merged",
            "github_pr": "https://github.com/example/project/pull/42",
        }

        updated, found, changed, _ = write_obsidian.merge_jira_task_into_existing(self.note, task)

        self.assertTrue(found)
        self.assertFalse(changed)
        self.assertEqual(updated, self.note)

    def test_when_jira_activity_completes_an_existing_task_it_should_update_status_and_remove_next(self):
        task = {
            "jira_ticket": "CNTRLPLANE-123",
            "descriptions": ["Merged the change."],
            "status": "completed",
            "upnext_description": "",
            "github_pr": "https://github.com/example/project/pull/42",
        }

        updated, found, changed, _ = write_obsidian.merge_jira_task_into_existing(self.note, task)

        self.assertTrue(found)
        self.assertTrue(changed)
        self.assertIn("**Status:** Completed", updated)
        self.assertNotIn("**Next:**", updated)
        self.assertIn("- Merged the change.", updated)

    def test_when_jira_activity_has_no_existing_task_it_should_leave_the_note_unchanged(self):
        task = {
            "jira_ticket": "CNTRLPLANE-999",
            "descriptions": ["Updated a Jira-only task."],
            "status": "in progress",
        }

        updated, found, changed, _ = write_obsidian.merge_jira_task_into_existing(self.note, task)

        self.assertFalse(found)
        self.assertFalse(changed)
        self.assertEqual(updated, self.note)

    def test_when_multiple_sources_have_the_same_ticket_it_should_coalesce_descriptions_and_prs(self):
        tasks = [
            {
                "jira_ticket": "CNTRLPLANE-123",
                "title": "Update test fixtures",
                "descriptions": ["Refreshed the fixture baseline."],
                "status": "in progress",
                "github_pr": "https://github.com/example/project/pull/42",
            },
            {
                "jira_ticket": "CNTRLPLANE-123",
                "descriptions": ["Refreshed the fixture baseline.", "Changed Jira status."],
                "status": "completed",
                "github_pr": "https://github.com/example/project/pull/44",
            },
        ]

        merged = write_obsidian.coalesce_authored_tasks(tasks)

        self.assertEqual(len(merged), 1)
        self.assertEqual(
            merged[0]["descriptions"],
            ["Refreshed the fixture baseline.", "Changed Jira status."],
        )
        self.assertEqual(merged[0]["github_prs"], [
            "https://github.com/example/project/pull/42",
            "https://github.com/example/project/pull/44",
        ])
        self.assertEqual(merged[0]["status"], "in progress")


if __name__ == "__main__":
    unittest.main()
