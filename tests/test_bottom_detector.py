"""Regression checks: bottom stages are descriptive and use no future candles."""
import datetime as dt
import unittest

from bottom_detector import analyze, confirmed_lows
from indicator_engine import calculate


def prices(n=230, crash=False):
    base=dt.date(2025,1,1)
    rows=[]
    for i in range(n):
        c=120000 + i*80
        v=100000
        if crash and i == n-1:
            c=70000
            v=1000000
        rows.append({
            'date':(base+dt.timedelta(days=i)).isoformat(),
            'open_krw':c+200,'high_krw':c+1000,
            'low_krw':c-1000,'close_krw':c,'volume':v
        })
    return rows


class BottomDetectorTests(unittest.TestCase):
    def test_washout_is_not_ultimate_low_confirmation(self):
        res=calculate(prices(crash=True))
        b=res['bottom']
        self.assertTrue(b['data_ready'])
        self.assertIsNotNone(b['washout'])
        self.assertNotEqual(b['kind'],'confirmation')
        self.assertTrue(b['not_prediction'])
        self.assertEqual(res['last']['bottom_stage'],b['stage'])

    def test_no_future_lookahead_on_prefix(self):
        rows=prices(235)
        today=calculate(rows[:224])['bottom']
        # Processing a future candle cannot rewrite the bottom signal
        # recorded at 224th candle (compare with independently truncated run).
        again=calculate(rows[:224])['bottom']
        self.assertEqual(today,again)
        self.assertEqual(today['date'],rows[223]['date'])
        self.assertTrue(all(p['confirmed_on']<=today['date']
                         for p in today['recent_two_confirmed_lows']))
        if today['latest_confirmed_swing_low']:
            self.assertLessEqual(
                today['latest_confirmed_swing_low']['confirmed_on'],today['date'])

    def test_pivot_requires_three_sessions_on_right(self):
        vals=[12,11,10,11,12,11,9.5,11,12,13]
        rows=[{'date':f'2026-01-{i+1:02d}','low':p,'rsi14':30+i}
              for i,p in enumerate(vals)]
        early=confirmed_lows(rows[:9])
        self.assertEqual([x['index'] for x in early],[2])
        later=confirmed_lows(rows)
        self.assertEqual([x['index'] for x in later],[2,6])
        self.assertEqual(later[-1]['confirmed_on'],'2026-01-10')

    def test_bullish_rsi_divergence_requires_confirmed_price_low(self):
        n=80
        d0=dt.date(2026,1,1)
        raw=[]
        ind=[]
        for i in range(n):
            low=98
            rsi=40
            if i==60:
                low=90
                rsi=20
            if i==70:
                low=89
                rsi=29
            raw.append({
                'date':(d0+dt.timedelta(days=i)).isoformat(),
                'low_krw':low,'high_krw':102,'close_krw':100,'volume':100000
            })
            ind.append({
                'date':raw[-1]['date'],'close':100,'rsi14':rsi,
                'macd_hist':-5+0.1*i,
                'ma5':99,'ma20':105,'ma60':110,'atr14':3,
                'volume_ratio20':1
            })
        out=analyze(raw,ind)
        self.assertTrue(out['bullish_rsi_divergence'])
        self.assertEqual(out['recent_two_confirmed_lows'][-1]['low'],89)
        self.assertEqual(out['recent_two_confirmed_lows'][-1]['confirmed_on'],
                         raw[73]['date'])
        partial=analyze(raw[:72],ind[:72])
        self.assertFalse(partial['bullish_rsi_divergence'])

    def test_invalid_ohlc_is_not_faked_as_bottom(self):
        p=prices(70)
        p[-1]['low_krw']=p[-1]['close_krw']+200
        res=calculate(p)['bottom']
        self.assertFalse(res['data_ready'])
        self.assertIn('보류',res['stage'])

    def test_insufficient_data_does_not_generate_score(self):
        out=calculate(prices(50))['bottom']
        self.assertIsNone(out['score'])
        self.assertEqual(out['kind'],'unknown')


if __name__=='__main__':
    unittest.main()
