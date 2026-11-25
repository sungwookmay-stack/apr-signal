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
        old_price = {'date':'2026-11-19','close_usd':26.37,'source':'Guinness Atkinson 운용사 공식 종가'}
        new_day = '2026-11-23'
        # This is a fixed scenario, not a copy of the rolling production snapshot.
        original = {
            'price_history': [old_price],
            'official_metrics': {
                'nav_usd': {'value':27.51,'as_of':new_day},
                'closing_market_price_usd': {'value':27.25,'as_of':new_day},
            },
            'apr_holdings_history': [{
                'as_of':'2026-11-19','ticker':'A278470','shares':86,
                'weight_pct':5.82,'market_value_usd':15743.74,
            }],
        }
        issuer_seed = {
            'source_url':'https://www.gafunds.com/kbty/',
            'status':'issuer snapshot','trading_confirmed':True,'inception_date':'2026-11-12',
            'official_data_state':'dated_issuer_data','holdings_as_of':'2026-11-19',
            'holdings':[],'holdings_scope':'issuer_apr_only','holdings_publication_state':'published',
            'official_metrics':{'nav_usd':{'value':27.06,'as_of':'2026-11-19'}},
        }
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
                root=Path(temp)
                (root/'config').mkdir()
                (root/'config'/'kbty_issuer_snapshot.json').write_text(json.dumps(issuer_seed))
                with patch.object(b,'ROOT',root), patch.object(b,'DATA',root), patch.object(b,'IMPORTS',root), patch.object(b,'fetch',side_effect=fetcher(document)):
                    b.save('kbty.json',original)
                    data=b.collect_kbty()
                    self.assertEqual((data['nav_usd'],data['nav_as_of']),(27.51,new_day))
                    self.assertEqual((data['latest_price_usd'],data['price_date']),(27.25,new_day))
                    self.assertIn(old_price,data['price_history'])
                    self.assertEqual(data['apr_holdings_history'][-1]['shares'],86)
