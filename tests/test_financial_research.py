import datetime as dt
import unittest
import financial_engine as fe

class APRFinancialResearchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=fe.build(fe.read_json(fe.INPUT))

    def test_2025_fourth_quarter_annual_less_nine_months(self):
        rows={x['period']:x for x in self.data['quarterly']}
        q=rows['2025Q4']
        self.assertIn('사업보고서',q['status'])
        for field,value in [('sales',5476.35),('op',1302.72),('ni',987.70),
                            ('ads',1000.07),('fees',1087.85),('logistics',357.66),
                            ('sga',2936.48),('cfo',1560.69),('capex',41.72),
                            ('fcf_proxy',1518.97)]:
            self.assertAlmostEqual(q[field],value,places=2,msg=field)
        self.assertEqual(q['available_from'],'2026-03-23')
        self.assertIn('/annual_report/',q['source_url'])
        self.assertAlmostEqual(self.data['annual'][-1]['op_income'],3655.21,2)

    def test_2026_third_quarter_missing_expenses_are_never_zero(self):
        rows={x['period']:x for x in self.data['quarterly']}
        last=rows['2026Q3']
        self.assertAlmostEqual(last['sales'],7731.15,2)
        self.assertAlmostEqual(last['op'],1606.40,2)
        self.assertIn('잠정',last['status'])
        for key in ['ads','sga','fees','logistics','cfo','capex',
                    'ads_ratio_pct','shipping_ratio_pct','cash_conversion_pct']:
            self.assertIsNone(last[key],key)
        self.assertAlmostEqual(last['op_margin_pct'],20.78,places=1)

    def test_inventory_and_working_capital_from_user_reports(self):
        balances={x['period']:x for x in self.data['balance']}
        h=balances['2026Q2']
        self.assertAlmostEqual(h['inventory'],3698.84,2)
        self.assertAlmostEqual(h['reported_inventory_turnover'],2.2,1)
        self.assertAlmostEqual(h['inventory_assets_pct'],33.56,2)
        self.assertAlmostEqual(balances['2025FY']['inventory_assets_pct'],21.44,2)
        self.assertAlmostEqual(h['inventory_days_company'],365/2.2,places=1)
        self.assertGreater(h['receivables'],1900)

    def test_roe_is_labeled_as_derived_not_reported(self):
        rs=self.data['roe_ttm']
        self.assertGreaterEqual(len(rs),1)
        self.assertTrue(all(x.get('method') for x in rs))
        self.assertTrue(all(x['roe_ttm_pct']>0 for x in rs))
        self.assertTrue(all(x['period']!='2026Q3' for x in rs))
        self.assertIn('ROIC',self.data['quality_notice'])

    def test_per_pbr_point_in_time_prevents_lookahead(self):
        p=self.data['valuation']
        eps=p['eps_events'];book=p['book_events']
        self.assertEqual(p['period_start'],'2025-06-01')
        self.assertEqual(eps[0]['available_from'],'2025-08-14')
        self.assertEqual(eps[0]['eps_won'],2875)
        self.assertEqual(eps[-1]['available_from'],'2026-10-30')
        self.assertIn('preliminary',eps[-1]['eps_quality'])
        self.assertAlmostEqual(eps[-1]['eps_won'],12493,delta=20)
        self.assertEqual(book[-1]['available_from'],'2026-08-14')
        self.assertFalse(any(x['asof']=='2026-09-30' for x in book))
        self.assertFalse(p['forward_or_consensus_used'])
        self.assertEqual(p['per_multiples'],[15,25,35,45,55])

if __name__=='__main__':unittest.main()
