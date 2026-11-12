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
        self.assertEqual(v['eps_events'][0]['available_from'],'2025-03-22')
        self.assertFalse(v['forward_or_consensus_used'])
        # No 2026 earnings event should be applied to 2025 prices.
        asof='2025-06-20'
        eligible=[x for x in v['eps_events'] if x['available_from']<=asof]
        self.assertEqual(len(eligible),2)
        fy=next(x for x in v['eps_events'] if x['asof']=='2025-12-31')
        self.assertEqual(fy['available_from'],'2026-03-24')

    def test_roic_missing_when_invested_capital_unverified(self):
        self.assertNotIn('roic_pct',self.out)
        self.assertIn('ROIC',self.out['quality_notice'])
        for x in self.out['roe_ttm']:
            self.assertTrue(x['method'])
            self.assertGreater(x['roe_ttm_pct'],0)


if __name__=='__main__':
    unittest.main()

class ComparativeBasisTests(unittest.TestCase):
    def test_2026_growth_uses_reviewed_restatement_without_mutating_history(self):
        import copy
        source=fe.read_json(fe.INPUT); before=copy.deepcopy(source)
        out=fe.build(source); rows={r['period']:r for r in out['quarterly']}
        self.assertEqual(source,before)
        for period,original,restated in [('Q1',545.68,556.27),('Q2',845.52,812.58),('Q3',961.28,950.91)]:
            prior=rows['2025'+period]; current=rows['2026'+period]
            self.assertEqual(prior['op'],original)
            self.assertEqual(current['yoy_comparative']['op'],restated)
            self.assertEqual(current['op_yoy_pct'],round((current['op']/restated-1)*100,2))
            self.assertIn('재작성',current['growth_comparison']['yoy']['status'])
        self.assertAlmostEqual(rows['2026Q3']['op_yoy_pct'],68.93)
        self.assertIsNone(rows['2026Q1']['op_qoq_pct'])
        self.assertIsNotNone(rows['2026Q2']['op_qoq_pct'])
        self.assertIn('apr-in.aprd.io',rows['2026Q3']['source_url'])

    def test_mismatched_or_missing_basis_never_falls_back(self):
        current={'period':'2026Q1','income_accounting_basis':'K-IFRS1118'}
        original={'period':'2025Q1','income_accounting_basis':'old','op':100}
        self.assertIsNone(fe.growth_comparison(current,original)[0])
        self.assertIsNone(fe.growth_comparison(current,original,{**original,'income_accounting_basis':'K-IFRS1118'})[0])
        explicit={**original,'period':'2025Q2','income_accounting_basis':'K-IFRS1118','source_url':'https://official.example'}
        self.assertIsNone(fe.growth_comparison(current,original,explicit)[0])
