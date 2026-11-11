import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import build_data as b

class PDPIntegration(unittest.TestCase):
    def test_retired_saved_pdp_does_not_reach_dashboard(self):
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
                self.assertEqual(first['amazon'],[])
                b.collect_demand()
                self.assertEqual(json.loads((data/'demand.json').read_text())['amazon'],[])

    def test_offline_build_removes_retired_pdp_preserving_other_data(self):
        from build_research_data import sync_saved_pdp
        row={'date':'2026-11-11','country':'US','asin':'B09V7Z4TJG','category':'Beauty','bsr':6,'source_quality':'verified_product_rank'}
        with tempfile.TemporaryDirectory() as temp:
            data=Path(temp)
            (data/'demand.json').write_text(json.dumps({'updated_at':'original-source-time','amazon':[row],'top100':[{'legacy':True}],'other':'preserved'}))
            (data/'scrapedo_pdp.json').write_text(json.dumps([row]))
            with patch.object(b,'fetch',side_effect=AssertionError('No network')), patch.object(b,'collect_demand',side_effect=AssertionError('No collector')):
                first=sync_saved_pdp(data,[{'code':'US','amazon':'amazon.com'}])
                self.assertEqual(first['amazon'],[])
                self.assertEqual(first['updated_at'],'original-source-time')
                self.assertEqual(first['other'],'preserved')
                self.assertNotIn('top100',first)
                self.assertEqual(sync_saved_pdp(data,[{'code':'US','amazon':'amazon.com'}]),first)
