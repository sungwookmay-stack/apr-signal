import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_data as b

class PDPIntegration(unittest.TestCase):
    def test_valid_saved_pdp_reaches_dashboard_without_new_requests(self):
        row={'date':'2026-11-11','country':'US','asin':'B09V7Z4TJG',
             'category':'Beauty & Personal Care','bsr':6,
             'source_quality':'verified_product_rank','source':'Scrape.do Amazon PDP'}
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);(root/'config').mkdir();data=root/'data';data.mkdir()
            (root/'config/markets.json').write_text(json.dumps({'markets':[{'code':'US','amazon':'amazon.com'}]}))
            (data/'scrapedo_pdp.json').write_text(json.dumps([row,dict(row,date='invalid')]))
            with patch.object(b,'ROOT',root), patch.object(b,'DATA',data), patch.object(b,'IMPORTS',root/'imports'), patch.dict(os.environ,{'APISH_KEY':'','SCRAPEDO_TOKEN':''}), patch.object(b,'fetch',side_effect=AssertionError('No network')):
                b.collect_demand()
                first=json.loads((data/'demand.json').read_text())
                self.assertEqual(first['amazon'],[row])
                b.collect_demand()
                self.assertEqual(json.loads((data/'demand.json').read_text())['amazon'],[row])
