import unittest
from customs_monthly import parse_body,DataError
class CustomsTests(unittest.TestCase):
 def xml(self,items):return '<response><header><resultCode>00</resultCode></header><body><items>'+items+'</items></body></response>'
 def row(self,hs,v):return f'<item><year>2026.10</year><statCd>US</statCd><hsCd>{hs}</hsCd><expDlr>{v}</expDlr></item>'
 def test_children_not_total(self):
  x=self.xml('<item><year>총계</year><expDlr>30</expDlr></item>'+self.row('3304991000',10)+self.row('3304999000',20))
  self.assertEqual(parse_body(x,'country','US','202610','202610'),{('US','2026-10'):30})
 def test_hs4_return(self):
  self.assertEqual(parse_body(self.xml(self.row('3304',30)),'country','US','202610','202610'),{('US','2026-10'):30})
 def test_overlap_rejected(self):
  with self.assertRaises(DataError):parse_body(self.xml(self.row('3304',30)+self.row('3304991000',10)),'country','US','202610','202610')
 def test_bad_total(self):
  with self.assertRaises(DataError):parse_body(self.xml('<item><year>총계</year><expDlr>31</expDlr></item>'+self.row('3304991000',10)),'country','US','202610','202610')
 def test_duplicates(self):
  with self.assertRaises(DataError):parse_body(self.xml(self.row('3304991000',10)*2),'country','US','202610','202610')
 def test_missing_not_zero(self):self.assertEqual(parse_body(self.xml(''),'country','US','202610','202610'),{})
 def test_region_raw_unit(self):
  x=self.xml('<item><priodTitle>2026.10</priodTitle><sggNm>서울특별시 송파구</sggNm><hsSgn>330499</hsSgn><expUsdAmt> 104,478</expUsdAmt></item>')
  self.assertEqual(parse_body(x,'regional','서울특별시 송파구','202610','202610'),{('서울특별시 송파구','2026-10'):104478})
if __name__=='__main__':unittest.main()
