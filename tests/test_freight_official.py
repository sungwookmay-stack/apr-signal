"""Offline regression tests for monthly Korea Customs freight-cost collection."""
import datetime as dt
import unittest
from urllib.parse import parse_qs, urlparse

from freight_official import parse_release, collect_release_links, fetch_latest, LIST_URL

SEPT_HTML = """
<html><body><h1>2026년 9월 수출입 운송비용 현황</h1>
<p>□〔해상수출〕전월대비 주요 운임 증감</p>
<table><tr><th>구분</th><th>평균 운송비용</th></tr>
<tr><td>미국서부</td><td>9,511 천원</td></tr>
<tr><td>미국동부</td><td>9,339 천원</td></tr>
<tr><td>유럽연합</td><td>5,040 천원</td></tr>
</table>
<p>□〔해상수입〕</p>
<table><tr><td>미국서부</td><td>1,886 천원</td></tr>
<tr><td>미국동부</td><td>1,552 천원</td></tr>
<tr><td>유럽연합</td><td>900 천원</td></tr></table>
</body></html>
"""
OCT_HTML = SEPT_HTML.replace('9월','10월').replace('9,511','8,900')\
    .replace('9,339','8,100').replace('5,040','4,200')
SEPT_URL = ('https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do'
            '?bbsId=1362&mi=2891&nttSn=10179764')
OCT_URL = ('https://www.customs.go.kr/kcs/na/ntt/selectNttInfo.do'
           '?bbsId=1362&mi=2891&nttSn=10182000')
LIST_HTML = f"""
<div>
 <a href="/kcs/na/ntt/selectNttInfo.do?bbsId=1362&amp;mi=2891&amp;nttSn=10182000">
  2026년 10월 수출입 운송비용 현황</a>
 <a href="/kcs/na/ntt/selectNttInfo.do?bbsId=1362&amp;mi=2891&amp;nttSn=10179764">
  2026년 9월 수출입 운송비용 현황</a>
 <a href="/kcs/na/ntt/selectNttInfo.do?nttSn=10182001">
  2026년 10월 수출입 현황 [잠정치]</a>
</div>
"""

class TestCustomsFreight(unittest.TestCase):
    def test_september_official_export_cost_not_import(self):
        row=parse_release(SEPT_HTML,SEPT_URL)
        self.assertEqual(row,{'month':'2026-09','us_west':9511,
                              'us_east':9339,'eu':5040})

    def test_does_not_use_import_values_for_export(self):
        data=SEPT_HTML.replace('9,511','—').replace('9,339','—')
        self.assertIsNone(parse_release(data,SEPT_URL))

    def test_does_not_create_unknown_month(self):
        self.assertIsNone(parse_release(
            SEPT_HTML.replace('2026년 9월 수출입 운송비용 현황',
                              '2026년 10월 수출입 잠정 현황'),SEPT_URL))

    def test_links_include_only_transport_cost_releases(self):
        links=collect_release_links(LIST_HTML)
        self.assertEqual(len(links),2)
        self.assertEqual(links[0],('2026-10',OCT_URL))
        self.assertEqual(links[1],('2026-09',SEPT_URL))

    def test_selects_latest_only_when_official_release_exists(self):
        calls=[]
        def fake(url,timeout):
            calls.append(url)
            if 'selectNttList' in url:return LIST_HTML.encode()
            if '10182000' in url:return OCT_HTML.encode()
            return SEPT_HTML.encode()
        row,url=fetch_latest(fake,today=dt.date(2026,11,5),pages=1)
        self.assertEqual(row['month'],'2026-10')
        self.assertEqual(row['us_west'],8900)
        self.assertEqual(url,OCT_URL)

    def test_older_official_release_not_treated_as_october(self):
        html=LIST_HTML.replace('2026년 10월 수출입 운송비용 현황',
                               '2026년 10월 수출입 잠정 현황')
        def fake(url,timeout):
            if 'selectNttList' in url:return html.encode()
            return SEPT_HTML.encode()
        row,url=fetch_latest(fake,today=dt.date(2026,11,5),pages=1)
        self.assertEqual(row['month'],'2026-09')
        self.assertEqual(row['us_west'],9511)

if __name__=='__main__':unittest.main()
