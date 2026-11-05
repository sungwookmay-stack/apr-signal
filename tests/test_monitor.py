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
    def test_ecb_cross_rates_from_matching_daily_fixing(self):
        sample=("Date, USD, JPY, KRW,\n"
                "2026-05-04, 1.2000, 130.0, 1500.00,\n"
                "2026-05-05, 1.1000, 128.0, 1540.00,\n"
                "2026-05-06, N/A, 128.0, 1530.00,\n")
        # Small synthetic fixture must be repeated across valid business days
        # to satisfy the historical data completeness threshold.
        base=dt.date(2026,5,4)
        rows=["Date, USD, KRW,"]
        for i in range(45):
            d=base+dt.timedelta(days=i)
            rows.append(f"{d.isoformat()}, 1.2, 1500.00,")
        values=update_data.parse_ecb_reference_csv(("\n".join(rows)+"\n").encode())
        self.assertEqual(values['EUR']['2026-05-04'],1500)
        self.assertAlmostEqual(values['USD']['2026-05-04'],1250,6)
        self.assertEqual(len(values['USD']),45)

    def test_bsr_never_confused_with_search_position(self):
        self.assertIsNone(api.first_bsr({'search_position':1}))
        self.assertEqual(api.first_bsr({'best_sellers_rank':[{'rank':456,'category':'Beauty'}]}),(456,'Beauty'))
        self.assertIsNone(api.first_bsr({'best_sellers_rank':[]}))
    def test_search_product_is_actual_brand(self):
        p=['medicube PDRN pink peptide serum','medicube zero pore pad']
        self.assertEqual(api.canon_product('MEDICUBE Zero Pore Pads 70pcs',p),p[1])
        self.assertIsNone(api.canon_product('Generic collagen jelly cream',p))
    def test_latin_america_markets_and_google_terms(self):
        import json
        from pathlib import Path
        cfg=json.loads((Path(__file__).resolve().parents[1] /
                        'config/markets.json').read_text(encoding='utf-8'))
        markets={x['code']:x for x in cfg['markets']}
        self.assertEqual(len(markets),16)
        self.assertEqual(sum(bool(x.get('amazon')) for x in markets.values()),12)
        for country in ('BR','AR','CL'):
            self.assertEqual(markets[country]['region'],'남미')
            self.assertEqual(len(api.terms_for_country(cfg,country)),5)
        self.assertEqual(markets['BR']['amazon'],'amazon.com.br')
        self.assertIsNone(markets['AR']['amazon'])
        self.assertIsNone(markets['CL']['amazon'])
        self.assertIn('medicube',api.terms_for_country(cfg,'BR'))
        self.assertIn('medicube',api.terms_for_country(cfg,'AR'))
    def test_new_latam_trends_bootstrap_after_regular_update(self):
        import tempfile
        from unittest.mock import patch
        from pathlib import Path
        class FakeBudget:
            today=dt.date(2026,11,5)
            stats={'attempted_credits':30,
                   'last_trends_run_day':'2026-11-05'}
            def __init__(self):
                self.called=[]
            def remaining(self):
                return 100
            def get(self,route,params,cost):
                self.called.append(params['geo'])
                terms=params['q'].split(',')
                return {'interest_over_time':[
                    {'time':'2026-11-05','values':{t:40 for t in terms}}
                ]}
        config={'markets':[{'code':'US'},{'code':'BR'},{'code':'AR'}],
                'trends_terms':{'default':['medicube'],
                     'BR':['medicube','medicube pdrn'],
                     'AR':['medicube','medicube pdrn']}}
        prev=[{'date':'2026-11-04','country':'US','term':'medicube',
               'index':65,'source':'API.SH Google Trends 공공 검색지수'}]
        budget=FakeBudget()
        with tempfile.TemporaryDirectory() as d:
            with patch.object(api,'STATE',Path(d)/'usage.json'):
                rows,n=api.update_trends(budget,config,prev)
                self.assertEqual(n,2)
                self.assertEqual(sorted(budget.called),['AR','BR'])
                self.assertEqual({r['country'] for r in rows},{'US','BR','AR'})
                again,n2=api.update_trends(budget,config,rows)
                self.assertEqual(n2,0)
                self.assertEqual(budget.called.count('BR'),1)
                self.assertEqual(budget.called.count('AR'),1)
    def test_latin_country_failed_locale_can_retry_same_day_once(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        class FakeBudget:
            today=dt.date(2026,11,5)
            stats={'last_trends_run_day':'2026-11-05',
                   'last_trends_attempt_by_country':{'AR':'2026-11-05','CL':'2026-11-05'}}
            def __init__(self):self.calls=[]
            def remaining(self):return 100
            def get(self,route,params,cost):
                self.calls.append((params['geo'],params['hl']))
                return {'interest_over_time':[{'time':'2026-11-05',
                        'values':{t:30 for t in params['q'].split(',')}}]}
        cfg={'markets':[{'code':'BR'},{'code':'AR'},{'code':'CL'}],
             'trends_terms':{'BR':['medicube'],'AR':['medicube'],'CL':['medicube']}}
        prev=[{'date':'2026-11-04','country':'BR','term':'medicube','index':60,
               'source':'API.SH Google Trends 공공 검색지수'}]
        budget=FakeBudget()
        with tempfile.TemporaryDirectory() as p:
            with patch.object(api,'STATE',Path(p)/'usage.json'):
                rows,n=api.update_trends(budget,cfg,prev)
                self.assertEqual(n,2)
                self.assertEqual(sorted(budget.calls),[('AR','en-US'),('CL','en-US')])
                rows2,n2=api.update_trends(budget,cfg,rows)
                self.assertEqual(n2,0)
                self.assertEqual(len(budget.calls),2)
    def test_no_paid_key_needed(self):
        self.assertIsNone(api.Budget('').get('google-trends/v1/interest',{'q':'medicube'},1))

if __name__=='__main__':unittest.main()
