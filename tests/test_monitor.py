import datetime as dt
import pathlib
import sys
import unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import indicator_engine as ind
import optional_free_api as api
import update_data

class MonitorTests(unittest.TestCase):
    def make_prices(self,n,trend=1):
        start=dt.date(2025,7,1)
        return [{'date':(start+dt.timedelta(days=i)).isoformat(),
                 'close_krw':200000+i*trend,'high_krw':201000+i*trend,
                 'low_krw':199000+i*trend,'volume':100000+i} for i in range(n)]
    def test_insufficient_data_never_suggests_entry(self):
        t=ind.calculate(self.make_prices(50));self.assertEqual(t['last']['kind'],'unknown')
        self.assertFalse(t['last']['fully_ready'])
        self.assertIn('유보',t['last']['averaging_down'])
    def test_daily_technical_last_with_220_candles(self):
        t=ind.calculate(self.make_prices(220));self.assertTrue(t['last']['fully_ready'])
        d=t['series'][-1]
        for k in ['bb_upper','bb_lower','cloud_a','cloud_b','rsi14','macd','atr14','ma200']:
            self.assertIsNotNone(d[k],k)
        self.assertLess(d['bb_lower'],d['bb_upper'])
        self.assertLessEqual(d['rsi14'],100)
    def test_no_ichimoku_future_lookahead(self):
        rows=self.make_prices(130)
        a=ind.calculate(rows)['series'][80]['cloud_a']
        for r in rows[81:]:r['high_krw']*=3;r['close_krw']*=3;r['low_krw']=r['close_krw']-10
        b=ind.calculate(rows)['series'][80]['cloud_a']
        self.assertEqual(a,b)
    def test_mixed_currency_calculation(self):
        stock=[{'date':'2026-05-04','close_krw':200000,'high_krw':201000,'low_krw':199000,'open_krw':199200,'volume':50}]
        fx={'USD':{'2026-05-04':1400.0},'EUR':{'2026-05-04':1600.0}}
        out=update_data.pack(stock,'test',fx,{},[],{}, {'sea':[],'air':[]})
        self.assertAlmostEqual(out['series'][0]['close_usd'],142.8571,4)
        self.assertEqual(out['series'][0]['fx_usd_date'],'2026-05-04')
    def test_bsr_never_confused_with_search_position(self):
        self.assertIsNone(api.first_bsr({'search_position':1}))
        self.assertEqual(api.first_bsr({'best_sellers_rank':[{'rank':456,'category':'Beauty'}]}),(456,'Beauty'))
        self.assertIsNone(api.first_bsr({'best_sellers_rank':[]}))
    def test_search_product_is_actual_brand(self):
        p=['medicube PDRN pink peptide serum','medicube zero pore pad']
        self.assertEqual(api.canon_product('MEDICUBE Zero Pore Pads 70pcs',p),p[1])
        self.assertIsNone(api.canon_product('Generic collagen jelly cream',p))
    def test_no_paid_key_needed(self):
        self.assertIsNone(api.Budget('').get('google-trends/v1/interest',{'q':'medicube'},1))

if __name__=='__main__':unittest.main()
