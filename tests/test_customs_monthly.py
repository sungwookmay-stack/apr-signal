import unittest
from customs_monthly import parse_body,DataError,country_specs
import json
import os,tempfile
from unittest.mock import patch
from pathlib import Path
class CustomsTests(unittest.TestCase):
 def test_all_demand_markets_and_china(self):
  config=json.loads(Path('config/markets.json').read_text())
  specs=country_specs(config)
  self.assertEqual({x[1] for x in specs},{x['code'] for x in config['markets']}|{'CN'})
  self.assertEqual(len(specs),17)
  self.assertIn('GB',{x[1] for x in specs})
 def test_no_duplicate_china_or_market(self):
  self.assertEqual(len(country_specs({'markets':[{'code':'CN'},{'code':'CN'}]})),1)
 def test_unknown_country_fails_closed(self):
  with self.assertRaises(DataError):country_specs({'markets':[{'code':'ZZ'}]})
 def test_each_country_response_identity(self):
  for _,code,_,_ in country_specs(json.loads(Path('config/markets.json').read_text())):
   body=self.xml(self.row('3304',30).replace('<statCd>US</statCd>',f'<statCd>{code}</statCd>'))
   self.assertEqual(parse_body(body,'country',code,'202610','202610'),{(code,'2026-10'):30})
 def test_retry_only_failed_windows_preserves_other_series(self):
  import customs_monthly as c
  root=Path.cwd()
  good={'id':'CN_3304','errors':[],'observations':[{'month':'2022-01','value':9}]}
  bad={'id':'US_3304','errors':[{'window':['202201','202212'],'code':'transport_error'}], 'verified_windows':[], 'observations':[{'month':'2021-12','value':8}]}
  good.update(status='success',latest_month='2022-01')
  # Minimal config avoids unrelated markets; preverified regions stay untouched.
  regions=[{'id':x,'errors':[],'observations':[]} for x in ['songpa_330499','geumcheon_330499','hwaseong_330499']]
  for r in regions:r.update(status='success',latest_month=None)
  with tempfile.TemporaryDirectory() as d:
   try:
    os.chdir(d);Path('data').mkdir();Path('config').mkdir()
    Path('data/customs_monthly.json').write_text(json.dumps({'series':[bad,good]+regions}))
    Path('config/markets.json').write_text(json.dumps({'markets':[{'code':'US'}]}))
    body=self.xml(self.row('3304',30).replace('2026.10','2022.01'))
    with patch.dict(os.environ,{'CUSTOMS_RETRY_FAILED':'true','CUSTOMS_COUNTRY_API_KEY':'test','CUSTOMS_REGIONAL_API_KEY':'test'}),patch.object(c,'fetch',return_value=body) as fetch,patch.object(c.time,'sleep'),patch('builtins.print'):
     c.main()
    self.assertEqual(fetch.call_count,1)
    result={x['id']:x for x in json.loads(Path('data/customs_monthly.json').read_text())['series']}
    self.assertEqual(result['CN_3304'],good)
    self.assertEqual(result['US_3304']['errors'],[])
    self.assertEqual(result['US_3304']['observations'][0],bad['observations'][0])
   finally:os.chdir(root)
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
