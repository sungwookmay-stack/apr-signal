import unittest
from kbty_official import parse_official

class Official(unittest.TestCase):
 def test_prelaunch_is_not_live(self):
  s=parse_official('Launching November 2026 KBTY is expected to begin trading November 12, 2026. Fund facts NAV— Closing market price— # of holdings 25 Performance Holdings will appear here once the daily holdings feed reports this fund.')
  self.assertEqual(s['launch_expected_date'],'2026-11-12')
  self.assertEqual(s['holdings_publication_state'],'not_published')
  self.assertEqual(s['official_metrics'],{})
 def test_undated_is_not_dated_history(self):
  s=parse_official('Fund facts NAV $25.20 Net assets $2.5M Closing market price $25.30 Performance NAV: The dollar value of a single share 900')
  self.assertEqual(s['official_metrics']['aum_usd']['value'],2500000)
  self.assertIsNone(s['official_metrics']['nav_usd']['as_of'])
 def test_unknown_does_not_claim_unpublished(self):
  s=parse_official('Access denied')
  self.assertEqual(s['official_data_state'],'unrecognized_page')
 def test_no_fake_nav_from_prose(self):
  s=parse_official('Fund facts Expense ratio 0.55% Performance NAV $25.20')
  self.assertEqual(s['official_metrics'],{})
