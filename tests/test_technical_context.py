import unittest
from indicator_engine import calculate
import datetime as dt

class TechnicalContextTests(unittest.TestCase):
    def rows(self,n=220):
        return [{"date":(dt.date(2025,1,1)+dt.timedelta(days=i)).isoformat(),"close_krw":200000+i,"high_krw":201000+i,"low_krw":199000+i,"volume":100000+i} for i in range(n)]
    def test_prior_range_excludes_today_and_future(self):
        rows=self.rows(); a=calculate(rows)['series'][50]
        rows[50]['high_krw']*=3
        rows[51]['high_krw']*=4
        b=calculate(rows)['series'][50]
        self.assertEqual(a['prior20_high'],b['prior20_high'])
        self.assertEqual(a['prior20_low'],b['prior20_low'])
        self.assertIsNone(calculate(rows[:20])['series'][-1]['prior20_high'])
    def test_volume_uses_prior_20_not_today(self):
        rows=self.rows(21)
        for r in rows:r['volume']=100
        rows[-1]['volume']=1000
        x=calculate(rows)['series'][-1]
        self.assertEqual(x['volume_ratio_prior20'],10)
        self.assertEqual(x['volume_ma20'],145)
        rows[-1]['volume']=0
        self.assertEqual(calculate(rows)['series'][-1]['volume_ratio_prior20'],0)
    def test_missing_volume_not_zero(self):
        rows=self.rows();rows[-1]['volume']=None
        x=calculate(rows)['series'][-1]
        self.assertIsNone(x['volume']);self.assertIsNone(x['volume_ratio_prior20'])
    def test_corrupt_high_low_invalidates_atr_and_restarts(self):
        rows=self.rows();rows[-15]['high_krw']=1
        out=calculate(rows)
        self.assertEqual(out['invalid_high_low_days'],1)
        self.assertIsNone(out['series'][-15]['atr14'])
        self.assertIsNone(out['series'][-2]['atr14'])
        self.assertIsNotNone(out['series'][-1]['atr14'])
    def test_nonfinite_close_filtered(self):
        rows=self.rows();rows[-1]['close_krw']=float('nan')
        self.assertEqual(calculate(rows)['data_days'],219)
