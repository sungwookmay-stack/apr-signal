import copy
import unittest
import financial_engine as fe
from valuation_audit import reconcile

class AuditTests(unittest.TestCase):
    def test_mismatch_not_overwritten(self):
        source={'balance':[{'period':'2025FY','equity':100}]}
        dart={'filings':[{'period':'2025FY','accounts':{'equity':{'value_won':200*1e8}}}]}
        r=reconcile(source,dart)['rows'][0]
        self.assertEqual(r['status'],'mismatch')
        self.assertEqual(source['balance'][0]['equity'],100)
    def test_missing_not_zero(self):
        r=reconcile({'annual':[{'period':'2025FY','net_income':100}]},{})['rows'][0]
        self.assertIsNone(r['dart_100m'])
        self.assertEqual(r['status'],'unverified')
    def test_unverified_table_cannot_replace_verified_eps(self):
        source=fe.read_json(fe.INPUT)
        first=fe.build(source)['valuation']['eps_events'][-1]
        source['quarterly'][-1]['ni']+=100
        updated=fe.build(source)['valuation']['eps_events'][-1]
        self.assertEqual(updated,first)
