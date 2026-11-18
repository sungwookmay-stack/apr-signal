import unittest
import datetime as dt
from unittest.mock import patch
from device_customs_monthly import collect_device_series
from device_customs_monthly import parse_device, windows
from customs_monthly import DataError

def xml(hs='8543702020',country='US',value='100',total='100'):
 return f'<r><resultCode>00</resultCode><item><year>2026.10</year><hsCd>{hs}</hsCd><statCd>{country}</statCd><expDlr>{value}</expDlr></item><item><year>총계</year><expDlr>{total}</expDlr></item></r>'
class DeviceTests(unittest.TestCase):
 def test_retry_preserves_complete_series_without_requests(self):
  before={'id':'US_8543702020','observations':[{'month':'2026-10','value':100}], 'errors':[], 'status':'success'}
  with patch('device_customs_monthly.country_specs',return_value=[('country','US','US_3304','미국')]),patch('device_customs_monthly.fetch') as f:
   result=collect_device_series({},[before],'test',dt.datetime.now(dt.timezone.utc),'202610',retry_only=True)
  self.assertEqual(result,[before]);f.assert_not_called()
 def test_retry_requests_failed_window_only(self):
  before={'id':'US_8543702020','observations':[{'month':'2025-06','value':80}], 'errors':[{'window':['202610','202610'],'code':'transport_error'}]}
  with patch('device_customs_monthly.country_specs',return_value=[('country','US','US_3304','미국')]),patch('device_customs_monthly.fetch',return_value=xml()) as f,patch('device_customs_monthly.time.sleep'):
   result=collect_device_series({},[before],'test',dt.datetime.now(dt.timezone.utc),'202610',retry_only=True)
  self.assertEqual(f.call_count,1);self.assertEqual(result[0]['status'],'success');self.assertEqual(len(result[0]['observations']),2)
 def test_valid(self):self.assertEqual(parse_device(xml(),'US','202610','202610'),{'2026-10':100})
 def test_wrong_hs(self):
  with self.assertRaises(DataError):parse_device(xml(hs='854370'),'US','202610','202610')
 def test_wrong_country(self):
  with self.assertRaises(DataError):parse_device(xml(country='CN'),'US','202610','202610')
 def test_total(self):
  with self.assertRaises(DataError):parse_device(xml(total='101'),'US','202610','202610')
 def test_zero(self):self.assertEqual(parse_device(xml(value='0',total='0'),'US','202610','202610')['2026-10'],0)
 def test_initial_windows(self):self.assertEqual(windows('202610',{}),[('202506','202512'),('202601','202610')])
 def test_incremental(self):
  obs={f'{y}-{m:02}':{} for y in [2025,2026] for m in range(1,13)}
  self.assertEqual(windows('202610',obs),[('202608','202610')])
 def test_missing_not_zero(self):self.assertEqual(parse_device('<r><resultCode>00</resultCode></r>','US','202610','202610'),{})
if __name__=='__main__':unittest.main()
