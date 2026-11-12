"""Offline APR SIGNAL schedule checks: no extra paid-API requests at 16:00."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / '.github/workflows/update-and-publish.yml'


class TwiceDailyNewsSchedule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workflow = WORKFLOW.read_text(encoding='utf-8')

    def section(self, name):
        return self.workflow.split('      - name: '+name, 1)[1].split('      - name:', 1)[0]

    def test_schedules_are_0730_and_1600_kst(self):
        self.assertIn("- cron: '30 22 * * *'", self.workflow)
        self.assertIn("- cron: '0 7 * * *'", self.workflow)
        self.assertIn("- cron: '30 11 * * *'", self.workflow)
        self.assertIn("- cron: '30 7 * * *'", self.workflow)
        self.assertEqual(self.workflow.count("- cron:"), 4)

    def test_only_morning_runs_paid_eligible_data_collector(self):
        morning = self.section('Fetch data, calculate signals, update verified news')
        self.assertIn("github.event.schedule == '30 22 * * *'", morning)
        self.assertNotIn("github.event.schedule == '0 7 * * *'", morning)
        self.assertIn('run: python build_data.py', morning)
        self.assertIn('APISH_KEY:', morning)
        self.assertNotIn('SCRAPEDO_TOKEN:', self.workflow)
        decodo=self.section('Decodo Top50 gated morning collection')
        self.assertIn("github.event_name == 'schedule' && github.event.schedule == '30 22 * * *'",decodo)
        self.assertNotIn('workflow_dispatch',decodo)
        self.assertIn('DECODO_API_KEY:',decodo)

    def test_afternoon_includes_stock_technicals_and_news_without_api_keys(self):
        afternoon = self.section(
            'Afternoon and evening - recheck free daily prices, indicators and news'
        )
        self.assertIn("github.event.schedule == '0 7 * * *'", afternoon)
        self.assertIn('run: python afternoon_refresh.py', afternoon)
        self.assertNotIn('run: python build_data.py', afternoon)
        self.assertNotIn('APISH_KEY:', afternoon)
        self.assertNotIn('SCRAPEDO_TOKEN:', afternoon)

    def test_night_investor_collection_does_not_run_paid_global_collector(self):
        flow = self.section('Collect APR investor, pension, short and KSD lending (free)')
        self.assertIn("github.event.schedule == '30 11 * * *'", flow)
        self.assertIn('run: python flows_collect.py', flow)
        self.assertNotIn('APISH_KEY:', flow)
        self.assertNotIn('SCRAPEDO_TOKEN:', flow)

    def test_manual_modes_preserved_and_public_deployment_stopped(self):
        news = self.section('News-only manual refresh')
        self.assertIn("'[news-now]'", news)
        self.assertIn('from build_data import collect_news; collect_news()', news)
        self.assertNotIn("github.event.schedule == '0 7 * * *'", news)
        self.assertIn("'[afternoon-now]'", self.workflow)
        self.assertIn("'[translate-now]'", self.workflow)
        self.assertIn("'[collect-now]'", self.workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", self.workflow)
        self.assertNotIn('actions/deploy-pages@', self.workflow)
        self.assertNotIn('actions/upload-pages-artifact@', self.workflow)
        self.assertIn('Store historical snapshots in repo', self.workflow)


if __name__ == '__main__':
    unittest.main()
