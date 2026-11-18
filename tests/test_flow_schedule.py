"""Two daily slots, with direct KRX collection disabled."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class FlowScheduleTests(unittest.TestCase):
 def test_only_two_slots(self):
  s=(ROOT/'.github/workflows/update-and-publish.yml').read_text()
  self.assertEqual(s.count('- cron:'),2)
  for cron in ('30 22 * * *','30 14 * * *'): self.assertIn("- cron: '"+cron+"'",s)
  for cron in ('30 7 * * *','0 7 * * *','30 11 * * *'): self.assertNotIn(cron,s)
 def test_no_direct_krx_calls_or_install(self):
  w=(ROOT/'.github/workflows/update-and-publish.yml').read_text()
  s=(ROOT/'flows_collect.py').read_text().split('def collect():',1)[1]
  self.assertNotIn('pip install --disable-pip-version-check --quiet pykrx',w)
  self.assertNotIn('from pykrx',s)
  self.assertIn("krx_mode='disabled_by_owner'",s)
  self.assertIn("daily=list(prior.get('daily',[]))",s)
  self.assertIn("shorts=list(prior.get('short_daily',[]))",s)
 def test_fsc_retired_and_history_untouched(self):
  from unittest.mock import patch
  from fsc_stock_lending import collect, update, get_for_day
  w=(ROOT/'.github/workflows/update-and-publish.yml').read_text()
  self.assertNotIn('FSC_STOCK_LENDING_API_KEY',w)
  self.assertNotIn('python fsc_stock_lending.py',w)
  before=(ROOT/'data/flows.json').read_bytes()
  with patch('urllib.request.urlopen',side_effect=AssertionError('No FSC network')):
   rows,meta=collect([{'date':'2026-11-17'}],key='offline-test')
   self.assertEqual(meta['status'],'disabled_by_owner')
   self.assertEqual(rows,[])
   self.assertEqual(update()['queries'],0)
   with self.assertRaises(PermissionError): get_for_day('2026-11-17','offline-test')
  self.assertEqual(before,(ROOT/'data/flows.json').read_bytes())
  s=(ROOT/'flows_collect.py').read_text()
  self.assertNotIn('fsc_stock_lending(',s)
  self.assertIn("fsc_result={'status':'disabled_by_owner','queries':0,'rows':0}",s)
