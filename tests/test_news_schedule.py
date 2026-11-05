"""No-cost APR SIGNAL news schedule regression checks (no paid API calls)."""
import pathlib
import unittest

ROOT=pathlib.Path(__file__).resolve().parents[1]
WORKFLOW=ROOT/'.github/workflows/update-and-publish.yml'

class TwiceDailyNewsSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow=WORKFLOW.read_text(encoding='utf-8')

    def test_morning_0730_and_afternoon_1600_kst_cron(self):
        self.assertIn("- cron: '30 22 * * *'",self.workflow)
        self.assertIn("- cron: '0 7 * * *'",self.workflow)
        self.assertEqual(self.workflow.count("- cron:"),2,
                         "No new third paid-collection schedule")

    def test_afternoon_only_runs_news_not_full_data_collector(self):
        full=self.workflow.split('      - name: Fetch data, calculate signals, update verified news',1)[1].split('      - name:',1)[0]
        news=self.workflow.split('      - name: Fetch US and other local news only without Amazon or paid APIs',1)[1].split('      - name:',1)[0]
        self.assertIn("github.event.schedule == '30 22 * * *'",full)
        self.assertNotIn("github.event.schedule == '0 7 * * *'",full)
        self.assertIn('run: python build_data.py',full)
        self.assertIn("github.event.schedule == '0 7 * * *'",news)
        self.assertNotIn('run: python build_data.py',news)
        self.assertIn('from build_data import collect_news; collect_news()',news)
        self.assertNotIn('APISH_KEY:',news)
        self.assertNotIn('SCRAPEDO_TOKEN:',news)

    def test_existing_manual_and_news_now_paths_preserved(self):
        self.assertIn("github.event_name == 'workflow_dispatch'",self.workflow)
        self.assertIn("'[collect-now]'",self.workflow)
        self.assertIn("'[news-now]'",self.workflow)
        self.assertIn("'[translate-now]'",self.workflow)
        self.assertIn('actions/deploy-pages@v4',self.workflow)

if __name__=='__main__':
    unittest.main()
