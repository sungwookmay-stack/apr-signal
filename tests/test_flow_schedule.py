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
