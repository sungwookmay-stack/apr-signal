"""Offline coverage for APR SIGNAL 16:00 close-price indicators and news."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import afternoon_refresh as ar
import build_data
import update_data


class AfternoonRefreshTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.kst = dt.datetime.fromisoformat('2026-11-05T16:05:00+09:00')
        (self.root / 'status.json').write_text(json.dumps({
            'generated_at_utc':'2026-11-05T00:00:00+00:00',
            'news_count':12,'trends_points':1000,'amazon_points':88,
            'beauty_leaderboard_snapshots':20,'kbty_status':'이전 발표',
            'errors':['오전 NLIC 갱신 실패']},ensure_ascii=False),
            encoding='utf-8')
        (self.root / 'bootstrap.js').write_text(
            'window.APR_BOOTSTRAP = ' + json.dumps({
                'demand':{'api_mode':'free_api_sh','amazon':[{'asin':'B123456789'}]},
                'kbty':{'ticker':'KBTY'}, 'reference_signals':{'foo':1},
                'status':{'news_count':12}
            })+';\n',encoding='utf-8')

    def make_rows(self, date):
        market={'meta':{'stock_last':date,'coverage_start':'2025-07-01',
                        'usd_fx_last':'2026-11-04','stock_source':'네이버 공개 일봉',
                        'errors':[]},
                'series':[{'date':date,'close_krw':254000,
                           'high_krw':260000,'low_krw':250000,'volume':400000}],
                'fx':[{'date':'2026-11-04','usdkrw':1325,'eurkrw':1500}],
                'logistics':{'sea':[{'month':'2026-09','us_west':9511,
                                      'us_east':9339,'eu':5040}]}}
        tech={'last':{'date':date,'source':'네이버 공개 일봉',
                      'label':'중립 / 확인 대기'},
              'series':[{'date':date,'rsi14':49,'ma200':230000}],
              'valid_high_low':210}
        news={'items':[{'title':'US Medicube',
                         'country':'US','title_ko':'미국 메디큐브 뉴스'}]}
        return market,tech,news

    def run_mock(self, date):
        market,tech,news=self.make_rows(date)
        with patch.object(build_data,'DATA',self.root),\
             patch.object(build_data,'errors',[]),\
             patch.object(build_data,'collect_market',return_value=(market,tech)) as stock,\
             patch.object(build_data,'collect_news',return_value=news) as collector,\
             patch.object(update_data,'iso_today_kr',return_value=self.kst):
            result=ar.refresh()
        stock.assert_called_once_with(refresh_fx=False,refresh_freight=False)
        collector.assert_called_once_with()
        status=json.loads((self.root/'status.json').read_text(encoding='utf-8'))
        bootstrap=json.loads((self.root/'bootstrap.js').read_text(encoding='utf-8')
                             .removeprefix('window.APR_BOOTSTRAP = ').rstrip(';\n'))
        return result,status,bootstrap

    def test_same_day_stock_close_refresh_updates_technical_and_news(self):
        result,status,payload=self.run_mock('2026-11-05')
        self.assertEqual(result['stock_date'],'2026-11-05')
        self.assertEqual(status['technical_last'],'2026-11-05')
        self.assertEqual(status['price_last'],'2026-11-05')
        self.assertTrue(status['afternoon_verified_same_day'])
        self.assertEqual(status['news_count'],1)
        self.assertIn('오전 NLIC 갱신 실패',status['errors'])
        self.assertEqual(payload['technical']['last']['date'],'2026-11-05')
        self.assertEqual(payload['news']['items'][0]['title_ko'],'미국 메디큐브 뉴스')
        self.assertEqual(payload['demand']['amazon'][0]['asin'],'B123456789')
        self.assertEqual(payload['kbty']['ticker'],'KBTY')
        self.assertEqual(payload['reference_signals']['foo'],1)
        self.assertEqual(payload['market']['logistics']['sea'][0]['month'],'2026-09')
        self.assertEqual(result['amazon_trends_api_calls'],0)

    def test_unavailable_today_close_is_not_falsely_marked_current(self):
        result,status,payload=self.run_mock('2026-11-04')
        self.assertFalse(status['afternoon_verified_same_day'])
        self.assertIn('마지막 확인 거래일',status['afternoon_note'])
        self.assertEqual(payload['technical']['last']['date'],'2026-11-04')

    def test_update_data_afternoon_skips_fx_and_freight_fetch(self):
        previous={
          'meta':{'stock_last':'2026-11-04','stock_source':'이전 확인',
                  'fx_sources':{'USD':'ECB','EUR':'ECB'}},
          'series':[{'date':'2026-11-04','close_krw':251000,'volume':300000,
                     'open_krw':250000,'high_krw':255000,'low_krw':248000}],
          'fx':[{'date':'2026-11-04','usdkrw':1300,'eurkrw':1490}],
          'logistics':{'unit':'천원/2TEU','sea':[{'month':'2026-09',
                          'us_west':9511,'us_east':9339,'eu':5040}]}}
        (self.root/'data.json').write_text(json.dumps(previous,ensure_ascii=False),
                                           encoding='utf-8')
        candles=[{'date':'2026-11-05','close_krw':255000,'volume':350000,
                  'open_krw':253000,'high_krw':257000,'low_krw':252000}]
        with patch.object(update_data,'fetch_stock',return_value=(candles,'무료 일봉',[])) as price,\
             patch.object(update_data,'fetch_fx',side_effect=AssertionError('FX must not run')),\
             patch.object(update_data,'fetch_sea_nlic',side_effect=AssertionError('NLIC must not run')),\
             patch.object(update_data,'fetch_customs_official_latest',
                          side_effect=AssertionError('Customs must not run')):
            result=update_data.update(self.root,refresh_fx=False,refresh_freight=False)
        price.assert_called_once()
        self.assertEqual(result['meta']['stock_last'],'2026-11-05')
        self.assertEqual(result['fx'][0]['usdkrw'],1300)
        self.assertEqual(result['logistics'],previous['logistics'])
        self.assertEqual(result['series'][0]['fx_usd_date'],'2026-11-04')

    def test_lagging_provider_does_not_rollback_saved_last_trading_day(self):
        previous={'meta':{'stock_last':'2026-11-05','stock_source':'confirmed',
                         'fx_sources':{'USD':'ECB','EUR':'ECB'}},
             'series':[{'date':'2026-11-05','close_krw':255000,
                        'open_krw':254000,'high_krw':260000,
                        'low_krw':252000,'volume':450000}],
             'fx':[{'date':'2026-11-04','usdkrw':1330,'eurkrw':1500}],
             'logistics':{'sea':[{'month':'2026-09','us_west':9511,
                                   'us_east':9339,'eu':5040}]}}
        (self.root/'data.json').write_text(json.dumps(previous,ensure_ascii=False),
                                           encoding='utf-8')
        lag=[{'date':'2026-11-04','close_krw':240000,'volume':300000,
             'open_krw':239000,'high_krw':244000,'low_krw':235000}]
        with patch.object(update_data,'fetch_stock',return_value=(lag,'지연된 데이터',[])):
            result=update_data.update(self.root,refresh_fx=False,refresh_freight=False)
        self.assertEqual(result['meta']['stock_last'],'2026-11-05')
        self.assertEqual(result['meta']['stock_source'],'confirmed')
        self.assertIn('기존 기록 유지',' '.join(result['meta']['errors']))


if __name__=='__main__':
    unittest.main()
