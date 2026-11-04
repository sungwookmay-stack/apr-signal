import unittest
from retail_reference_collector import parse_ulta, parse_target, parse_weekly, text_of

class RetailSignalParserTests(unittest.TestCase):
 def test_ulta_confirmed_filters(self):
  t="medicube 67 results Only at Ulta 3 Products Available 3 Online Only 35 Products Available 35"
  self.assertEqual(parse_ulta(t),{'catalog_items':67,'online_only_items':35,'exclusive_items':3})
 def test_ulta_rejects_invalid(self):
  self.assertEqual(parse_ulta("67 results unrelated brand"),{})
  self.assertEqual(parse_ulta("medicube 2 results Online Only 35 Products Available"),{'catalog_items':2})
 def test_target_context_specific(self):
  t="medicube 9 results 104k+ bought in last month $20.99 medicube Zero Pore Pad Korean Skincare"
  self.assertEqual(parse_target(t),{'category_items':9,'zero_pore_pad_bought_lower':104000})
 def test_target_rejects_non_matching_badges(self):
  t="medicube 9 results 104k+ bought in last month Other brand blah "+("foo "*80)+"medicube Zero Pore Pad"
  self.assertNotIn('zero_pore_pad_bought_lower',parse_target(t))
 def test_weekly_only_full_coverage(self):
  t="2026-W44 snapshot US Beauty best sellers observed 100/100 medicube medicube best product #2 · 8 items overall"
  self.assertEqual(parse_weekly(t),{'week':'2026-W44','count':8,'covered':100})
  self.assertIsNone(parse_weekly(t.replace('100/100','60/100')))
 def test_html_text_ignores_script(self):
  self.assertEqual(text_of("<html><script>fraud=5000</script><body>medicube <b>67 results</b></body></html>"),"medicube 67 results")
if __name__=='__main__':unittest.main()
