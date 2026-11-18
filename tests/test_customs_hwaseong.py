import unittest
from customs_monthly import parse_body,DataError,REGIONAL_SIDO

def xml(names):
 return '<response><resultCode>00</resultCode><items>'+''.join('<item><priodTitle>2026.10</priodTitle><hsSgn>330499</hsSgn><sggNm>'+n+'</sggNm><expUsdAmt>28914</expUsdAmt></item>' for n in names)+'</items></response>'
class HwaseongTests(unittest.TestCase):
 def test_city_only(self):
  self.assertEqual(REGIONAL_SIDO['경기도 화성시'],'41')
  self.assertEqual(parse_body(xml(['경기도 화성시']),'regional','경기도 화성시','202610','202610'),{('경기도 화성시','2026-10'):28914})
 def test_parent_child_and_child_only_rejected(self):
  for names in [['경기도 화성시','경기도 화성시 만세구'],['경기도 만세구'],['경기도 화성시 효행구'],['경기도 병점구'],['경기도 동탄구']]:
   with self.assertRaisesRegex(DataError,'regional_boundary_changed'):parse_body(xml(names),'regional','경기도 화성시','202610','202610')
 def test_seoul_response_rejected(self):
  with self.assertRaises(DataError):parse_body(xml(['서울특별시 송파구']),'regional','경기도 화성시','202610','202610')
 def test_duplicates_rejected(self):
  with self.assertRaises(DataError):parse_body(xml(['경기도 화성시']*2),'regional','경기도 화성시','202610','202610')
