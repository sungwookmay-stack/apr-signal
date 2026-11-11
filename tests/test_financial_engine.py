"""APR financial-source consistency; no future earnings on historical bands."""
import datetime as dt
import unittest
from pathlib import Path

import financial_engine as fe


class APRFinancialEngineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.out=fe.build(fe.read_json(fe.INPUT))

    def test_audited_q4_is_fully_populated(self):
        q=next(x for x in self.out['quarterly'] if x['period']=='2025Q4')
        self.assertEqual(q['sales'],5476.35)
        self.assertEqual(q['op'],1302.72)
        self.assertEqual(q['ads'],1000.07)
        self.assertEqual(q['fees'],1087.85)
        self.assertEqual(q['logistics'],357.66)
        self.assertEqual(q['cfo'],1560.69)
        self.assertEqual(q['capex'],41.72)
        self.assertAlmostEqual(q['fcf_proxy'],1518.97,places=2)
        self.assertIn('연간',q['status'])
        self.assertTrue(q['source_url'].startswith('https://'))

    def test_preliminary_2026_q3_does_not_invent_expenses(self):
        q=next(x for x in self.out['quarterly'] if x['period']=='2026Q3')
        self.assertAlmostEqual(q['sales'],7731.15)
        self.assertAlmostEqual(q['op'],1606.4)
        for key in ('ads','sga','fees','logistics','ads_ratio_pct','cfo'):
            self.assertIsNone(q[key],key)

    def test_revenue_and_inventory_checks(self):
        b=next(x for x in self.out['balance'] if x['period']=='2026Q2')
        self.assertAlmostEqual(b['inventory'],3698.84)
        self.assertAlmostEqual(b['inventory_assets_pct'],33.56,places=1)
        self.assertAlmostEqual(b['reported_inventory_turnover'],2.2)
        self.assertAlmostEqual(b['inventory_days_company'],165.91)

    def test_valuation_point_in_time_starts_before_june_2025(self):
        v=self.out['valuation']
        self.assertEqual(v['period_start'],'2025-06-01')
        self.assertEqual(v['per_multiples'],[15,25,35,45,55])
        self.assertEqual(v['pbr_multiples'],[5,10,15,20,25])
        self.assertEqual(v['eps_events'][0]['available_from'],'2025-08-14')
        self.assertFalse(v['forward_or_consensus_used'])
        # No 2026 earnings event should be applied to 2025 prices.
        asof='2025-06-20'
        eligible=[x for x in v['eps_events'] if x['available_from']<=asof]
        self.assertEqual(len(eligible),0)
        fy=next(x for x in v['eps_events'] if x['asof']=='2025-12-31')
        self.assertEqual(fy['available_from'],'2026-03-23')

    def test_roic_missing_when_invested_capital_unverified(self):
        self.assertNotIn('roic_pct',self.out)
        self.assertIn('ROIC',self.out['quality_notice'])
        for x in self.out['roe_ttm']:
            self.assertTrue(x['method'])
            self.assertGreater(x['roe_ttm_pct'],0)


if __name__=='__main__':
    unittest.main()
