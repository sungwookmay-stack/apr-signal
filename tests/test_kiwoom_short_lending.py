"""Offline mock tests for broker-provided short and stock lending data."""
import datetime as dt
import unittest

from kiwoom_short_lending import (
    SHORT_URL, LENDING_URL, short_rows,lending_rows,fetch_short_lending
)
from kiwoom_flows import TOKEN_URL
from flows_engine import evaluate


class KiwoomMarketTests(unittest.TestCase):
    def setUp(self):
        start=dt.date(2026,10,1)
        self.prices=[{'date':(start+dt.timedelta(days=i)).isoformat(),
                      'close_krw':100000+i*100,
                      'volume':1000000} for i in range(40)]
        self.dates={x['date'] for x in self.prices}

    def test_short_ratio_is_quantity_not_borrowed_balance_or_cash(self):
        d={'shrts_trnsn':[
            {'dt':'20261008','shrts_qty':'1,200','trde_qty':'10,000',
             'ovr_shrts_qty':'999,999','shrts_trde_prica':'30000'}]}
        rows=short_rows(d,{'2026-10-08'})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['short_trade_qty'],1200)
        self.assertEqual(rows[0]['short_volume_ratio_pct'],12)
        self.assertIsNone(rows[0]['short_value_ratio_pct'])
        self.assertIsNone(rows[0]['reported_net_short_balance_qty'])
        self.assertIsNone(rows[0]['short_trade_value_krw'])
        self.assertNotIn('ovr_shrts_qty',rows[0])

    def test_lending_new_repayment_balance_never_short_interest(self):
        d={'dbrt_trde_trnsn':[
            {'dt':'20261008','dbrt_trde_cntrcnt':'1,200',
             'dbrt_trde_rpy':'900','dbrt_trde_irds':'300',
             'rmnd':'20,000','remn_amt':'50,000'}]}
        rows=lending_rows(d,{'2026-10-08'})
        self.assertEqual(rows[0]['new_qty'],1200)
        self.assertEqual(rows[0]['returned_qty'],900)
        self.assertEqual(rows[0]['balance_qty'],20000)
        self.assertNotIn('reported_net_short_balance_qty',rows[0])

    def test_missing_all_short_or_lending_does_not_become_zero(self):
        d={'shrts_trnsn':[{'dt':'20261008','shrts_qty':None,'trde_qty':None}]}
        self.assertEqual(short_rows(d,{'2026-10-08'}),[])
        borrow={'dbrt_trde_trnsn':[
            {'dt':'20261008','dbrt_trde_cntrcnt':'',
             'dbrt_trde_rpy':None,'rmnd':None}]}
        self.assertEqual(lending_rows(borrow,{'2026-10-08'}),[])

    def test_signed_invalid_and_future_rows_filtered(self):
        resp={'dbrt_trde_trnsn':[
            {'dt':'20261008','dbrt_trde_cntrcnt':'-5','dbrt_trde_rpy':'0'},
            {'dt':'20261009','rmnd':'1000'}]}
        self.assertEqual(len(lending_rows(resp,{'2026-10-08'})),0)

    def test_read_only_two_api_calls_reuse_one_token(self):
        calls=[]
        def post(url,body,headers=None):
            calls.append((url,body,headers))
            if url==TOKEN_URL:
                self.assertEqual(body['grant_type'],'client_credentials')
                return {'return_code':0,'token':'TEST_TOKEN'},{}
            self.assertEqual(headers['authorization'],'Bearer TEST_TOKEN')
            if url==SHORT_URL:
                self.assertEqual(headers['api-id'],'ka10014')
                self.assertEqual(body['tm_tp'],'1')
                self.assertEqual(body['stk_cd'],'278470')
                return {'return_code':0,'shrts_trnsn':[
                    {'dt':'20261008','shrts_qty':'200',
                     'trde_qty':'1000'}]}, {'cont-yn':'N'}
            if url==LENDING_URL:
                self.assertEqual(headers['api-id'],'ka20068')
                self.assertEqual(body['all_tp'],'0')
                return {'return_code':0,'dbrt_trde_trnsn':[
                    {'dt':'20261008','dbrt_trde_cntrcnt':'500',
                     'dbrt_trde_rpy':'120','rmnd':'10000'}]}, {'cont-yn':'N'}
            raise AssertionError('Unsupported endpoint')
        sh, lending, meta=fetch_short_lending('KEY','SECRET',self.prices,post=post)
        self.assertEqual(len(calls),3)
        self.assertEqual(sh[0]['short_volume_ratio_pct'],20)
        self.assertEqual(lending[0]['balance_qty'],10000)
        self.assertTrue(meta['short']['read_only'])
        self.assertTrue(meta['lending']['read_only'])
        self.assertNotIn('TEST_TOKEN',str(meta))
        self.assertNotIn('SECRET',str(meta))

    def test_partial_short_api_failure_still_fetches_lending(self):
        def post(url,body,headers=None):
            if url==TOKEN_URL:
                return {'return_code':0,'token':'MOCK'},{}
            if url==SHORT_URL:
                return {'return_code':-1},{}
            return {'return_code':0,'dbrt_trde_trnsn':[
                {'dt':'20261008','rmnd':'3000'}]},{}
        short, lend, statuses=fetch_short_lending('k','s',self.prices,post=post)
        self.assertEqual(short,[])
        self.assertEqual(len(lend),1)
        self.assertEqual(statuses['short']['status'],'failed')
        self.assertEqual(statuses['lending']['status'],'ok')

    def test_20_day_short_ratio_requires_all_price_dates(self):
        prices=self.prices[-20:]
        shorts=[]
        for p in prices:
            shorts.append({'date':p['date'],'short_trade_qty':100,
                           'total_traded_qty':1000})
        result=evaluate(prices,[],shorts)
        self.assertEqual(result['short']['short_volume_period20_pct'],10)
        result=evaluate(prices,[],shorts[:-1])
        self.assertIsNone(result['short']['short_volume_period20_pct'])


if __name__=='__main__':
    unittest.main()
