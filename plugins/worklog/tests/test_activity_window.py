import importlib.util
import json
import shutil
import subprocess
import sys
import unittest
import tempfile
import io
from contextlib import redirect_stdout
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path


SCRIPTS = Path(__file__).parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("classify_prs", SCRIPTS / "classify-prs.py")
classifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(classifier)
from worklog_window import ActivityWindow, resolve_window


@unittest.skipUnless(shutil.which("jq"), "jq is needed to exercise the GitHub timestamp query")
class ActivityWindowTests(unittest.TestCase):
    def test_previous_evening_is_included_when_starting_a_new_day_from_since(self):
        timestamps = ["2026-11-12T21:27:06Z", "2026-11-12T23:00:00Z", "2026-11-13T13:00:00Z"]
        query = classifier.date_filter(".", "2026-11-13", "2026-11-12T21:27:06Z", "2026-11-13T13:00:00Z")
        result = subprocess.run(["jq", "[.[] | select(" + query + ")]"], input=json.dumps(timestamps),
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout), ["2026-11-12T23:00:00Z", "2026-11-13T13:00:00Z"])

    def test_upper_cutoff_is_inclusive_and_later_activity_is_deferred(self):
        query = classifier.date_filter(".", "2026-11-13", "2026-11-12T21:27:06Z", "2026-11-13T13:00:00Z")
        timestamps = ["2026-11-13T13:00:00Z", "2026-11-13T13:00:01Z"]
        run = subprocess.run(["jq", "[.[] | select(" + query + ")]"], input=json.dumps(timestamps), capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(run.stdout), ["2026-11-13T13:00:00Z"])

    def test_a_merge_in_the_window_is_logged_without_new_commits(self):
        detail = {"created_at": "2026-11-10T12:00:00Z", "merged_at": "2026-11-12T23:00:00Z", "closed_at": "2026-11-12T23:00:00Z"}
        def api(path, query):
            raw = detail if path.endswith('/pulls/42') else []
            return subprocess.run(['jq',query],input=json.dumps(raw),capture_output=True,text=True,check=True).stdout
        with patch.object(classifier, 'gh_api', side_effect=api):
            activity = classifier.fetch_authored_activity({'repo':'example/project','number':42},'2026-11-13','2026-11-12T21:27:06Z','bryan','2026-11-13T13:00:00Z')
        self.assertEqual(activity['lifecycle'], ['PR merged'])
        self.assertEqual(activity['commits'], [])

    def test_idle_open_related_pr_keeps_a_changed_jira_group_in_progress(self):
        common={'jira':'CNTRLPLANE-42','repo':'example/project','sources':['authored'],'isDraft':False}
        prs=[common|{'number':1,'title':'Finish one part','url':'https://github.com/example/project/pull/1','state':'closed'},
             common|{'number':2,'title':'Remaining part','url':'https://github.com/example/project/pull/2','state':'open'}]
        def activity(pr,*args):
            return {'commits':[],'reviews':[],'comments':[],'lifecycle':['PR merged'] if pr['number']==1 else []}
        output=io.StringIO()
        with patch.object(sys,'argv',['classifier','--date','2026-11-13']), patch.object(sys,'stdin',io.StringIO(json.dumps({'username':'bryan','since':'2026-11-12T21:27:06Z','until':'2026-11-13T13:00:00Z','prs':prs}))), patch.object(classifier,'fetch_authored_activity',side_effect=activity), redirect_stdout(output):
            classifier.main()
        tasks=json.loads(output.getvalue())['authored_tasks']
        self.assertEqual(len(tasks),1)
        self.assertEqual(tasks[0]['status'],'in progress')


class WatermarkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.vault = Path(self.temp.name)
        self.folder = self.vault / 'Work log/2026/11'
        self.folder.mkdir(parents=True)

    def tearDown(self):
        self.temp.cleanup()

    def note(self, day, watermark):
        (self.folder / (day+'.md')).write_text(f'# Daily Log · {day}\n\n*Last updated: {watermark}*\n')

    def test_new_day_continues_from_the_previous_note(self):
        self.note('2026-11-12','2026-11-12T21:27:06Z')
        result = resolve_window(self.vault,'2026-11-13',until='2026-11-13T13:00:00Z')
        self.assertEqual(result['since'],'2026-11-12T21:27:06Z')
        self.assertEqual(result['watermark_source'],str(self.folder/'2026-11-12.md'))
        self.assertTrue(ActivityWindow.for_date(result['date'],result['since'],result['until']).contains('2026-11-12T23:00:00Z'))

    def test_existing_day_uses_its_own_watermark(self):
        self.note('2026-11-12','2026-11-12T21:27:06Z')
        self.note('2026-11-13','2026-11-13T13:00:00Z')
        result=resolve_window(self.vault,'2026-11-13',until='2026-11-13T17:00:00Z')
        self.assertEqual(result['since'],'2026-11-13T13:00:00Z')

    def test_monday_continues_from_friday_instead_of_losing_weekend_activity(self):
        self.note('2026-11-13','2026-11-13T21:00:00Z')
        result=resolve_window(self.vault,'2026-11-16',until='2026-11-16T13:00:00Z')
        self.assertEqual(result['since'],'2026-11-13T21:00:00Z')

    def test_first_note_starts_at_local_midnight(self):
        result=resolve_window(self.vault,'2026-11-13',until='2026-11-13T13:00:00Z')
        self.assertEqual(result['since'],'')
        window=ActivityWindow.for_date(result['date'],result['since'],result['until'])
        self.assertTrue(window.contains('2026-11-13T05:00:00Z'))
        self.assertFalse(window.contains('2026-11-13T04:59:59Z'))

    def test_invalid_watermark_does_not_silently_skip_activity(self):
        self.note('2026-11-12','not-a-timestamp')
        with self.assertRaises(ValueError):resolve_window(self.vault,'2026-11-13',until='2026-11-13T13:00:00Z')


if __name__ == "__main__":
    unittest.main()
