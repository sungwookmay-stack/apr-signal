"""SEC KBTY monitoring: no unrelated trust filings, no invented holdings."""
import datetime as dt
import json
import tempfile
import unittest
import urllib.error
from unittest.mock import patch
from pathlib import Path

import kbty_sec as sec


class KbtySecTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / 'kbty_sec.json'
        self.now = dt.datetime.fromisoformat('2026-11-06T11:00:00+00:00')
        self.registry = sec.read_json(sec.SOURCE, {})
        self.registry['filings'] = [x for x in self.registry['filings'] if x['form'] != 'CERT']
        self.registry_file = Path(self.temp.name) / 'registry.json'
        sec.write_json(self.registry_file, self.registry)

    def test_curated_sec_timeline_and_performance_are_not_fabricated(self):
        out = sec.assemble_base(self.registry)
        self.assertEqual(out['series_id'], 'S000109351')
        self.assertEqual(out['registrant_cik'], '0000919160')
        self.assertEqual(out['latest_verified_filing_date'], '2026-10-28')
        self.assertEqual([x['form'] for x in out['filings']],
                         ['485BPOS', '485BXT', '485APOS'])
        self.assertTrue(any('0.55%' in x['summary'] for x in out['briefing']))
        self.assertTrue(any('에이피알' in x['implication'] for x in out['briefing']))
        self.assertNotIn('related_manager_filings', out)
        self.assertEqual(out['latest_verified_filing_date'], '2026-10-28')
        self.assertNotIn('apr_weight_pct', out)
        self.assertNotIn('aum_usd', out)
        self.assertIsNone(out['last_successful_check_utc'])

    def test_submissions_candidates_do_not_assert_sec_series_by_cik_alone(self):
        payload = {
            'cik': 919160,
            'filings': {'recent': {
                'accessionNumber': ['0001213900-26-116001',
                                    '0001213900-26-116002',
                                    '0001213900-26-113359'],
                'filingDate': ['2026-11-06', '2026-11-05', '2026-10-28'],
                'form': ['497', '497K', '485BPOS'],
                'primaryDocument': ['file_497.htm', 'funds_497k.htm',
                                    'ea0306550-01_485bpos.htm'],
            }}
        }
        rows=sec.candidate_filings(payload,min_date='2026-10-01')
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['accession'],'0001213900-26-116001')
        self.assertFalse(any(x.get('series_id')==sec.SERIES for x in rows))
        with self.assertRaises(ValueError):
            sec.candidate_filings({**payload, 'cik': 99999999})

    def test_match_exact_series_tag_never_company_or_unrelated_series(self):
        self.assertTrue(sec.has_target_series(b'<SERIES-ID>S000109351\n'
                                              b'<SERIES-NAME>Guinness Atkinson K-Beauty ETF'))
        self.assertFalse(sec.has_target_series(
            b'<SERIES-ID>S000005895\n<SERIES-NAME>Other Fund\n'
            b'<DESCRIPTION>K-Beauty ETF in a footnote'))
        self.assertFalse(sec.has_target_series(b'<SERIES-ID>S0001093518'))

    def test_detects_only_target_series_filing_and_marks_body_unreviewed(self):
        payload = {
            'cik': 919160, 'filings': {'recent': {
                'accessionNumber': ['0001213900-26-116003',
                                    '0001213900-26-116002',
                                    '0001213900-26-113359'],
                'filingDate': ['2026-11-06', '2026-11-05', '2026-10-28'],
                'form': ['497', '485BPOS', '485BPOS'],
                'primaryDocument': ['fund_notes.htm', 'other_fund.htm',
                                    'ea0306550-01_485bpos.htm']
            }}
        }
        called=[]
        def fake(url):
            called.append(url)
            if url == sec.SEC_SUBMISSIONS:
                return json.dumps(payload).encode()
            if '116003' in url:
                return b'<SERIES-ID>S000109351\n'
            return b'<SERIES-ID>S000005895\n'
        result = sec.refresh(registry_file=self.registry_file, transport=fake,output=self.output,now=self.now)
        self.assertEqual(result['new_detected'],1)
        self.assertEqual(result['latest_verified_filing_date'],'2026-11-06')
        self.assertEqual(result['last_successful_check_utc'],
                         '2026-11-06T11:00:00+00:00')
        self.assertEqual(len(result['filings']),4)
        newly = result['filings'][0]
        self.assertEqual(newly['form'],'497')
        self.assertEqual(newly['review_level'],
                         'KBTY 시리즈 확인 · 서식 기반 설명')
        self.assertIn('원문',newly['summary_ko'])
        self.assertNotIn('0001213900-26-116002',
                         [x['accession'] for x in result['filings']])
        self.assertEqual(len(called),3)
        self.assertTrue((self.output).exists())

    def test_free_sec_fulltext_fallback_is_identity_checked(self):
        sample = {'hits': {'hits': [
            {'_id':'0001213900-26-116010:filing.htm',
             '_source': {'form':'497','file_date':'2026-11-06',
                         'ciks':['0000919160']}},
            {'_id':'0001213900-26-116011:other.htm',
             '_source': {'form':'497','file_date':'2026-11-06',
                         'ciks':['0000123456']}},
            {'_id':'not-an-accession:malicious.htm',
             '_source': {'form':'485BPOS','file_date':'2026-11-06',
                         'ciks':['0000919160']}}
        ]}}
        called = []
        def mock(url):
            called.append(url)
            if url == sec.SEC_SUBMISSIONS:
                raise urllib.error.HTTPError(url,403,'Restricted',{},None)
            if url.startswith(sec.SEC_FULLTEXT):
                return json.dumps(sample).encode()
            if '116010' in url and url.endswith('index-headers.html'):
                return b'<SERIES-ID>S000109351\n'
            raise OSError('Unknown request')
        result = sec.refresh(registry_file=self.registry_file, transport=mock, output=self.output,now=self.now)
        self.assertEqual(result['new_detected'],1)
        self.assertEqual(len(result['filings']),4)
        self.assertEqual(result['filings'][0]['accession'],'0001213900-26-116010')
        self.assertIn('full-text',result['sec_monitor_status'])
        self.assertEqual(result['last_successful_check_utc'],
                         '2026-11-06T11:00:00+00:00')
        self.assertEqual(len(called),3)
        self.assertIn('ciks=0000919160',called[1])

    def test_sec_search_hit_for_other_cik_cannot_be_kbty(self):
        doc={'hits':{'hits':[
             {'_id':'0001213900-26-116010:other.htm',
              '_source':{'form':'497','file_date':'2026-11-06',
                         'ciks':['0000919159']}}
        ]}}
        self.assertEqual(sec.fulltext_candidates(doc),[])
        with self.assertRaises(ValueError):
            sec.fulltext_candidates({'hits':{}})

    def test_sec_header_access_failure_is_not_confirmed_latest(self):
        doc={'cik':919160,'filings':{'recent':{
             'accessionNumber':['0001213900-26-116010'],
             'filingDate':['2026-11-06'],'form':['497'],
             'primaryDocument':['kbty_filing.htm']}}}
        def response(url):
            if url==sec.SEC_SUBMISSIONS:
                return json.dumps(doc).encode()
            raise urllib.error.HTTPError(url,403,'Restricted',{},None)
        report=sec.refresh(registry_file=self.registry_file, transport=response,output=self.output,now=self.now)
        self.assertEqual(report['new_detected'],0)
        self.assertEqual(report['latest_verified_filing_date'],'2026-10-28')
        self.assertIsNone(report['last_successful_check_utc'])
        self.assertIn('미확정',report['sec_monitor_status'])

    def test_sec_403_or_error_preserves_old_verified_records(self):
        def blocked(url):
            raise urllib.error.HTTPError(url,403,'Forbidden',{},None)
        result=sec.refresh(registry_file=self.registry_file, transport=blocked,output=self.output,now=self.now)
        self.assertEqual(len(result['filings']),3)
        self.assertIn('접근 실패',result['sec_monitor_status'])
        self.assertIsNone(result['last_successful_check_utc'])
        self.assertEqual(result['sec_monitor_error'],'HTTPError')
        self.assertEqual([x['http_status'] for x in result['retrieval_diagnostics']],[403,403])
        self.assertNotIn('https:',str(result['retrieval_diagnostics']))
        self.assertIsNotNone(result['checked_at_utc'])

    def test_cert_is_not_filtered_out(self):
        payload={'cik':919160,'filings':{'recent':{'accessionNumber':['0001143362-26-000444'],'filingDate':['2026-11-10'],'form':['CERT'],'primaryDocument':['KBTY111026.pdf']}}}
        rows=sec.candidate_filings(payload)
        self.assertEqual(rows[0]['form'],'CERT')
        def transport(url):
            if url==sec.SEC_SUBMISSIONS: return json.dumps(payload).encode()
            return b'<CIK>0000919160'
        with patch.object(sec,'certificate_identity',return_value=True):
            result=sec.refresh(registry_file=self.registry_file,transport=transport,output=self.output,now=self.now)
        self.assertEqual(result['latest_verified_filing_date'],'2026-11-10')
        self.assertEqual(result['filings'][0]['review_level'],'CERT 원문 펀드명·거래소 확인')
        self.output.unlink()
        with patch.object(sec,'certificate_identity',return_value=False):
            result=sec.refresh(registry_file=self.registry_file,transport=transport,output=self.output,now=self.now)
        self.assertIsNone(result['last_successful_check_utc'])
        self.assertEqual(len(result['pending_review']),1)
        self.assertEqual(result['latest_verified_filing_date'],'2026-10-28')

    def test_http_diagnostics_do_not_expose_response_or_url(self):
        error=urllib.error.HTTPError('https://secret.invalid/?token=secret',429,'private response',{},None)
        detail=sec.failure_detail(error,'SEC submissions')
        self.assertEqual(detail['http_status'],429)
        self.assertNotIn('secret',str(detail))
        self.assertNotIn('private response',str(detail))

    def test_malicious_filename_or_wrong_company_cannot_create_sec_link(self):
        self.assertIsNone(sec.candidate_filings({
            'cik':919160,'filings':{'recent':{
                'accessionNumber':['../../oops'],
                'filingDate':['2026-11-06'],
                'form':['497'],
                'primaryDocument':['../../evil.htm']
            }}},min_date='2026-10-01')[0] if sec.candidate_filings({
            'cik':919160,'filings':{'recent':{
                'accessionNumber':['../../oops'],
                'filingDate':['2026-11-06'],
                'form':['497'],
                'primaryDocument':['../../evil.htm']
            }}},min_date='2026-10-01') else None)
        with self.assertRaises(ValueError):
            sec.filing_link('0001213900-26-116001','../../evil.htm')

    def test_existing_auto_detected_record_remains_after_network_failure(self):
        previous=sec.assemble_base(self.registry)
        item=sec.make_detected_record({
            'accession':'0001213900-26-116003',
            'filed_date':'2026-11-06', 'form':'497',
            'filename':'fund_notes.htm'})
        previous['filings'].insert(0,item)
        previous['last_successful_check_utc']='2026-11-06T09:00:00+00:00'
        sec.write_json(self.output,previous)
        result=sec.refresh(registry_file=self.registry_file, transport=lambda _: (_ for _ in ()).throw(
            OSError('unavailable')), output=self.output,now=self.now)
        self.assertEqual(result['latest_verified_filing_date'],'2026-11-06')
        self.assertEqual(len(result['filings']),4)
        self.assertEqual(result['last_successful_check_utc'],
                         '2026-11-06T09:00:00+00:00')


if __name__ == '__main__':
    unittest.main()
