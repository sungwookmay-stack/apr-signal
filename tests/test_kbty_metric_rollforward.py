import datetime as dt
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

import build_data as b


class KbtyMetricRollForward(unittest.TestCase):
    def test_newer_verified_values_survive_stale_or_failed_issuer(self):
        original = json.loads(Path('data/kbty.json').read_text())
        old_price = {'date':'2026-11-19','close_usd':26.37,'source':'Guinness Atkinson 운용사 공식 종가'}
        new_day = '2026-11-23'
        original['official_metrics']['nav_usd'] = {'value':27.51,'as_of':new_day}
        original['official_metrics']['closing_market_price_usd'] = {'value':27.25,'as_of':new_day}
        chart = json.dumps({'chart':{'result':[{
            'timestamp':[int(dt.datetime(2026,11,19,tzinfo=dt.timezone.utc).timestamp())],
            'indicators':{'quote':[{'close':[26.3734]}]}
        }]}}).encode()
        def fetcher(document):
            def fetch(url):
                if 'yahoo' in url:
                    return chart
                if document is None:
                    raise urllib.error.HTTPError(url,403,'Denied',{},None)
                return document
            return fetch
        for document in (None,b'Fund facts NAV (11/19/2026) $27.06 Performance'):
            with self.subTest(document=document), tempfile.TemporaryDirectory() as temp:
                with patch.object(b,'DATA',Path(temp)), patch.object(b,'fetch',side_effect=fetcher(document)):
                    b.save('kbty.json',original)
                    data=b.collect_kbty()
                    self.assertEqual((data['nav_usd'],data['nav_as_of']),(27.51,new_day))
                    self.assertEqual((data['latest_price_usd'],data['price_date']),(27.25,new_day))
                    self.assertIn(old_price,data['price_history'])
                    self.assertEqual(data['apr_holdings_history'][-1]['shares'],86)
