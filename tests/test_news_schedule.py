"""Offline APR SIGNAL schedule checks: no extra paid-API requests at 23:30."""
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

    def test_schedules_are_0730_and_2330_kst(self):
        self.assertIn("- cron: '30 22 * * *'", self.workflow)
        self.assertIn("- cron: '30 14 * * *'", self.workflow)
        self.assertEqual(self.workflow.count("- cron:"), 2)

    def test_only_morning_runs_paid_eligible_data_collector(self):
        morning = self.section('Fetch data, calculate signals, update verified news')
        self.assertIn("github.event.schedule == '30 22 * * *'", morning)
        self.assertNotIn("github.event.schedule == '30 14 * * *'", morning)
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
        self.assertIn("github.event.schedule == '30 14 * * *'", afternoon)
        self.assertIn('run: python afternoon_refresh.py', afternoon)
        self.assertNotIn('run: python build_data.py', afternoon)
        self.assertNotIn('APISH_KEY:', afternoon)
        self.assertNotIn('SCRAPEDO_TOKEN:', afternoon)

    def test_hosted_refresh_never_collects_or_rewrites_legacy_flows(self):
        self.assertNotIn('flows_collect.py', self.workflow)
        self.assertNotIn("'[flows-now]'", self.workflow)
        for secret in ('KSD_SLB_API_KEY', 'KIS_APP_KEY', 'KIWOOM_APP_KEY'):
            with self.subTest(secret=secret):
                self.assertNotIn(secret, self.workflow)
        guard = self.section('Verify legacy flow files were not changed')
        self.assertIn('git diff --exit-code HEAD -- data/flows.json data/flow_reference.json', guard)
        self.assertLess(self.workflow.index('Verify legacy flow files were not changed'),
                        self.workflow.index('- name: Store historical snapshots in repo'))

    def test_manual_modes_preserved_and_public_deployment_stopped(self):
        news = self.section('News-only manual refresh')
        self.assertIn("'[news-now]'", news)
        self.assertIn('from build_data import collect_news; collect_news()', news)
        self.assertNotIn("github.event.schedule == '30 14 * * *'", news)
        self.assertIn("'[afternoon-now]'", self.workflow)
        self.assertIn("'[translate-now]'", self.workflow)
        self.assertIn("'[collect-now]'", self.workflow)
        self.assertIn("github.event_name == 'workflow_dispatch'", self.workflow)
        self.assertNotIn('actions/deploy-pages@', self.workflow)
        self.assertNotIn('actions/upload-pages-artifact@', self.workflow)
        self.assertIn('Store historical snapshots in repo', self.workflow)


if __name__ == '__main__':
    unittest.main()
