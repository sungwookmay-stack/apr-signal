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
  self.assertIn('자동 수집 아님',s['source_note'])
 def test_failed_fetch_does_not_reassert_old_status(self):
  s=self.run_collector(ValueError('offline'))
  self.assertIn('현재 거래 여부 미확인',s['status'])
 def test_matching_phrase_only(self):
  s=self.run_collector(b'expected to begin trading in the second week of November')
  self.assertIn('11월 둘째 주',s['launch_expected'])
