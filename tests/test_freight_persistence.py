"""No network: reviewed freight survives next collector rebuild and failures."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import update_data
import build_data

class FreightPersistenceTests(unittest.TestCase):
    def test_display_review_survives_skipped_freight_and_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            old={'series':[{'date':'2026-11-18','close_krw':100}], 'fx':[],
                 'logistics':{'sea':[{'month':'2026-09','us_west':9511}], 'last_verified_month':'2026-08'}}
            reviewed={'sea':[{'month':'2026-10','us_west':9377}], 'last_verified_month':'2026-10',
                      'last_verified_at_utc':'2026-11-18', 'last_fetch_failed':True, 'last_fetch_errors':['HTTP 503']}
            (root/'data.json').write_text(json.dumps(old))
            (root/'market.json').write_text(json.dumps({'logistics':reviewed,'series':[{'date':'1900-01-01'}]}))
            with patch.object(update_data,'fetch_stock',return_value=([],None,[])):
                result=update_data.update(root,refresh_fx=False,refresh_freight=False)
            self.assertEqual(result['series'][0]['date'],'2026-11-18')
            self.assertEqual([r['month'] for r in result['logistics']['sea']],['2026-09','2026-10'])
            self.assertEqual(result['logistics']['last_verified_month'],'2026-10')
            self.assertTrue(result['logistics']['last_fetch_failed'])
            self.assertEqual(json.loads((root/'data.json').read_text())['logistics'],result['logistics'])
            with patch.object(build_data,'DATA',root), patch.object(update_data,'update',side_effect=RuntimeError('offline')), patch.object(build_data,'calculate',return_value={'last':None}):
                market,_=build_data.collect_market()
            self.assertEqual(market['logistics'],result['logistics'])

    def test_newer_collector_not_overwritten_by_old_display(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            for file,month in [('data.json','2026-11'),('market.json','2026-10')]:
                (root/file).write_text(json.dumps({'logistics':{'sea':[{'month':month}], 'last_verified_month':month}}))
            self.assertEqual(update_data.load_previous(root)['logistics']['last_verified_month'],'2026-11')
