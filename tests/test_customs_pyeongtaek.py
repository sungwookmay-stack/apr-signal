import unittest
from customs_monthly import DataError, REGIONAL_SIDO, relative_comparable, parse_body
from test_customs_hwaseong import xml


class PyeongtaekTests(unittest.TestCase):
 def test_exact_scope_and_missing(self):
  geo='경기도 평택시'
  self.assertEqual(REGIONAL_SIDO[geo], '41')
  self.assertEqual(parse_body(xml(['경기도 화성시',geo]),'regional',geo,'202610','202610'),{(geo,'2026-10'):28914})
  self.assertEqual(parse_body(xml(['경기도 화성시']),'regional',geo,'202610','202610'),{})

 def test_duplicate_subdivision_and_wrong_province(self):
  for names in [['경기도 평택시']*2,['경기도 평택시','경기도 평택시 송탄'],['서울특별시 금천구']]:
   with self.subTest(names=names), self.assertRaises(DataError):
    parse_body(xml(names),'regional','경기도 평택시','202610','202610')

 def test_wanju_contemporary_only(self):
  geo='전북특별자치도 완주군'
  self.assertEqual(REGIONAL_SIDO[geo], '52')
  self.assertEqual(parse_body(xml([geo]),'regional',geo,'202610','202610'),{(geo,'2026-10'):28914})
  for alias in ('전라북도 완주군','전북특별자치도 완주군 삼례읍'):
   try: rows=parse_body(xml([alias]),'regional',geo,'202610','202610')
   except DataError: continue
   self.assertEqual(rows,{})

 def test_complete_exact_months_and_windows_required(self):
  obs={'2024-01':1,'2024-02':0}
  windows=[['202401','202402']]
  self.assertTrue(relative_comparable(obs,[],windows,2024,'202402'))
  self.assertFalse(relative_comparable({'2024-01':1},[],windows,2024,'202402'))
  self.assertFalse(relative_comparable(obs,['failed'],windows,2024,'202402'))
  self.assertFalse(relative_comparable(obs,[],[],2024,'202402'))

 def test_expansion_only_keeps_other_series_unchanged_and_calls_only_41_52(self):
  import contextlib, io, json, os, tempfile
  from pathlib import Path
  from unittest.mock import patch
  import customs_monthly as c
  before=[{'id':'US_3304','observations':[{'month':'2026-08','value':4}]},{'id':'hwaseong_330499','metadata':{'preserve':True}}]
  original=Path.cwd()
  calls=[]
  def fake(kind,key,params):
   calls.append((kind,params.copy()))
   label='경기도 평택시' if params['sidoCd']=='41' else '전북특별자치도 완주군'
   month=f"{params['strtYymm'][:4]}.01"
   return xml([label]).replace('2026.10',month)
  with tempfile.TemporaryDirectory() as tmp:
   try:
    os.chdir(tmp);Path('config').mkdir();Path('data').mkdir()
    Path('config/markets.json').write_text('{"markets":[]}')
    Path('data/customs_monthly.json').write_text(json.dumps({'series':before}))
    with patch.dict(os.environ,{'CUSTOMS_REGIONAL_EXPANSION_ONLY':'true','CUSTOMS_REGIONAL_API_KEY':'fixture','CUSTOMS_RETRY_FAILED':'false'},clear=True), patch.object(c,'fetch',side_effect=fake),patch.object(c.time,'sleep'),contextlib.redirect_stdout(io.StringIO()):
     c.main()
    rows=json.loads(Path('data/customs_monthly.json').read_text())['series']
   finally:os.chdir(original)
  self.assertEqual(rows[:2],before)
  self.assertEqual({r['id'] for r in rows[2:]},{'pyeongtaek_330499','wanju_330499'})
  self.assertEqual({kind for kind,_ in calls},{'regional'})
  self.assertEqual({p['sidoCd'] for _,p in calls},{'41','52'})
  self.assertEqual(min(p['strtYymm'] for _,p in calls if p['sidoCd']=='52'),'202401')
  self.assertTrue(all(not r['relative_comparable'] for r in rows[2:]))
