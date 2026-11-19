import unittest
from unittest.mock import patch
import build_data
class KbtyProvenance(unittest.TestCase):
 def run_collector(self,document):
  saved={}
  def fetch(url):
   if 'gafunds' in url:
    if isinstance(document,Exception): raise document
    return document
   raise ValueError('no quote fixture')
  with patch.object(build_data,'fetch',side_effect=fetch),patch.object(build_data,'read_json',return_value={'status':'출시 준비 중 (공식 사이트)'}),patch.object(build_data,'load_csv',return_value=[]),patch.object(build_data,'save',side_effect=lambda n,v:saved.update({n:v})):
   return build_data.collect_kbty()
 def test_absent_launch_phrase_is_unknown(self):
  s=self.run_collector(b'<html>Fund facts unrelated</html>')
  self.assertEqual(s['status'],'현재 거래·상장 상태 미확인')
  self.assertIsNone(s['launch_expected'])
  self.assertIn('Yahoo',s['source_note'])
  self.assertIn('확인 자료 없음',s['source_note'])
 def test_failed_fetch_does_not_reassert_old_status(self):
  s=self.run_collector(ValueError('offline'))
  self.assertIn('현재 거래 여부 미확인',s['status'])
 def test_matching_phrase_only(self):
  s=self.run_collector(b'expected to begin trading in the second week of November')
  self.assertIn('11월 둘째 주',s['launch_expected'])

class SavedKbtySourceNormalization(unittest.TestCase):
 def test_official_fields_survive_late_run_and_only_note_changes(self):
  import json
  from pathlib import Path
  from tempfile import TemporaryDirectory
  from source_provenance import normalize_saved_sources
  with TemporaryDirectory() as work:
   p=Path(work)/'kbty.json'
   url='https://www.gafunds.com/kbty/'
   original=dict(official_url=url, price_date='2026-11-18', price_source='Guinness Atkinson 운용사 공식 종가',
      latest_price_usd=25.70, nav_usd=25.75, nav_as_of='2026-11-18', apr_holding_as_of='2026-11-18',
      apr_shares=86, apr_weight_pct=5.89, aum_usd=None,
      official_metrics=dict(closing_market_price_usd=dict(as_of='2026-11-18',value=25.70),
                            nav_usd=dict(as_of='2026-11-18',value=25.75)),
      holdings=[dict(as_of='2026-11-18',ticker='A278470',shares=86,weight_pct=5.89,source_url=url)],
      source_note='old generic Yahoo note')
   p.write_text(json.dumps(original))
   normalize_saved_sources(work)
   raw=p.read_bytes()
   saved=json.loads(raw)
   note=saved.pop('source_note')
   self.assertIn('운용사 공식 종가',note)
   self.assertIn('NAV: 운용사 공식',note)
   self.assertIn('APR 비중·보유주식수: 운용사 날짜별 보유 내역',note)
   self.assertIn('AUM: 확인 자료 없음',note)
   self.assertNotIn('Yahoo',note)
   original.pop('source_note')
   self.assertEqual(saved,original)
   normalize_saved_sources(work)
   self.assertEqual(p.read_bytes(),raw)

 def test_newer_yahoo_close_does_not_downgrade_official_nav_or_falsely_merge_dates(self):
  from source_provenance import kbty_source_note
  note=kbty_source_note(dict(official_url='https://www.gafunds.com/kbty/',latest_price_usd=26,
    price_date='2026-11-19',price_source='Yahoo Finance 비공식 일별시세',
    nav_as_of='2026-11-18',nav_usd=25.75,
    official_metrics={'closing_market_price_usd': {'value':25.70,'as_of':'2026-11-18'},
                      'nav_usd':{'value':25.75,'as_of':'2026-11-18'}}))
  self.assertIn('가격: Yahoo Finance',note)
  self.assertIn('NAV: 운용사 공식',note)
  self.assertNotIn('APR 비중',note)
