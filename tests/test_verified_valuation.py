import copy
import datetime as dt
import json
import unittest
from verified_valuation import SOURCE, build

class VerifiedValuationTests(unittest.TestCase):
    def setUp(self):
        self.manifest=json.loads(SOURCE.read_text())
        self.v=build(self.manifest)
    def test_latest_parent_ttm_reconstructed(self):
        e=self.v['eps_events'][-1]
        self.assertEqual(e['asof'],'2026-06-30')
        self.assertEqual(e['ttm_days'],365)
        expected_profit=289654813287-116250326398+258793447596
        expected_shares=(13615165790-6727925270+6776061055)/365
        self.assertAlmostEqual(e['shares'],expected_shares)
        self.assertEqual(e['eps_won'],round(expected_profit/expected_shares,2))
        self.assertEqual(e['reported_basic_eps_won'],6913) # H1 not TTM
        self.assertTrue(e['attributable_verified'])
    def test_treasury_removed_not_cancelled_twice(self):
        b={x['period']:x for x in self.v['book_events']}
        self.assertEqual(b['2024FY']['shares'],37241555)
        self.assertEqual(b['2025Q1']['shares'],36843155)
        self.assertEqual(b['2025Q2']['shares'],37430655)
        self.assertEqual(b['2025Q3']['shares'],37430655)
        self.assertEqual(b['2026Q2']['bps_won'],round(648033794500/37438155,2))
    def test_conflicting_day_count_is_excluded(self):
        bad=next(e for e in self.v['eps_events'] if e['period']=='2025Q2')
        self.assertIsNone(bad['eps_won'])
        self.assertIn('181',bad['quality_issue'])
        self.assertFalse(bad['attributable_verified'])
    def test_no_same_day_or_lookahead(self):
        for e in self.v['eps_events']:
            self.assertGreater(e['available_from'],e['published_on'])
            self.assertGreater(e['published_on'],e['asof'])
        self.assertFalse(any(e['period']=='2026Q3' for e in self.v['eps_events']))
    def test_eps_rounding_mismatch_fails_closed(self):
        m=copy.deepcopy(self.manifest)
        m['reports'][-1]['reported_basic_eps_won']+=100
        self.assertIsNone(build(m)['eps_events'][-1]['eps_won'])
    def test_missing_comparative_fails_closed(self):
        m=copy.deepcopy(self.manifest)
        m['reports']=[x for x in m['reports'] if x['period']!='2025FY']
        self.assertIsNone(build(m)['eps_events'][-1]['eps_won'])
    def test_invalid_previous_component_propagates(self):
        for field in ('reported_basic_eps_won','weighted_average_basic_shares'):
            m=copy.deepcopy(self.manifest)
            next(x for x in m['reports'] if x['period']=='2025FY')[field]+=100
            self.assertIsNone(build(m)['eps_events'][-1]['eps_won'])
    def test_split_not_applied_twice(self):
        self.assertAlmostEqual(self.v['eps_events'][0]['eps_won'],2875.37)
        self.assertEqual(self.v['corporate_actions'][0]['ratio'],5)
    def test_source_coverage(self):
        for r in self.v['primary_audit']:
            self.assertTrue(r['source_url'].startswith('https://'))
            self.assertIn('source_sha256', r)
