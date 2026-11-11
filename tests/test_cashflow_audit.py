"""Original-filing cash flow basis, never mix restated comparatives with originals."""
import unittest
import financial_engine as fe

class CashFlowAuditTests(unittest.TestCase):
    def setUp(self):
        self.q = {r['period']:r for r in fe.build(fe.read_json(fe.INPUT))['quarterly']}

    def test_each_quarter_uses_ytd_difference(self):
        for period, q in self.q.items():
            if period == '2026Q3':
                self.assertIsNone(q['cfo']); self.assertIsNone(q['fcf_proxy']); continue
            a=q['cash_flow_audit']
            self.assertEqual(q['cfo'],round((a['cfo_ytd_won']-a['prior_cfo_ytd_won'])/1e8,2))
            self.assertEqual(q['capex'],round((a['tangible_capex_ytd_won']-a['prior_tangible_capex_ytd_won'])/1e8,2))
            self.assertEqual(q['fcf_proxy'],round(q['cfo']-q['capex'],2))
            self.assertEqual(q['cash_conversion_pct'],round(100*q['cfo']/q['ni'],2))

    def test_original_2025_reconciles_to_annual(self):
        qs=[self.q['2025Q'+str(i)] for i in range(1,5)]
        self.assertAlmostEqual(sum(q['cfo'] for q in qs),3410.46397295,delta=.02)
        self.assertAlmostEqual(sum(q['capex'] for q in qs),154.11405167,delta=.02)
        self.assertEqual(qs[0]['cfo'],535.10)
        self.assertEqual(qs[1]['cfo'],656.03)
        self.assertEqual(qs[2]['capex'],35.39)
        self.assertEqual(qs[0]['fcf_proxy'],499.48)
        self.assertEqual(qs[1]['fcf_proxy'],614.65)

    def test_comparative_restatement_is_preserved_but_not_mixed(self):
        self.assertEqual(self.q['2025Q1']['cash_flow_audit']['restated_comparative_cfo_ytd_won'],51547432619)
        self.assertEqual(self.q['2025Q2']['cash_flow_audit']['restated_comparative_cfo_ytd_won'],116067068380)
        for p in ['2025Q1','2025Q2']:
            self.assertFalse(self.q[p]['cash_flow_audit']['restated_used_in_original_series'])
        self.assertAlmostEqual(self.q['2026Q1']['cfo']+self.q['2026Q2']['cfo'],864.04149570,delta=.01)
