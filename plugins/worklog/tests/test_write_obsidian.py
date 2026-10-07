import importlib.util
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "scripts" / "write-obsidian.py"
SPEC = importlib.util.spec_from_file_location("write_obsidian", SCRIPT)
write_obsidian = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(write_obsidian)


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
