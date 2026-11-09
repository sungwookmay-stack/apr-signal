"""KITA official route parser regression tests, no live network or paid API."""
import json
import tempfile
import unittest
from pathlib import Path
from kita_rates import parse_sea_rates, parse_sea_bulletin, parse_secondary_east, update, SEA_URL


class KitaRatesTests(unittest.TestCase):
    def test_grouped_cells_are_prices_plus_changes(self):
        html = """
        <table><tr><th>출발</th><th>도착</th><th>년</th><th>월</th>
        <th>TEU</th><th>FEU</th></tr>
        <tr><td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td>
        <td>6700 300</td><td>8500 600</td></tr>
        <tr><td>Busan</td><td>Long Beach</td><td>2026</td><td>09</td>
        <td>6400 200</td><td>7900 300</td></tr>
        </table>"""
        rows = sorted(parse_sea_rates(html), key=lambda x: x['month'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[-1]['month'], '2026-10')
        self.assertEqual(rows[-1]['feu_usd'], 8500)
        self.assertEqual(rows[-1]['teu_usd'], 6700)
        self.assertEqual(rows[-1]['source_url'], SEA_URL)

    def test_separate_dollar_delta_cells(self):
        html = """<table><tr>
        <td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td>
        <td>6700</td><td>300</td><td>8500</td><td>600</td></tr></table>"""
        self.assertEqual(parse_sea_rates(html)[0]['feu_usd'], 8500)

    def test_zero_is_missing_not_free_shipping(self):
        html = """<table><tr><td>Busan</td><td>Long Beach</td>
        <td>2026</td><td>10</td><td>0</td><td>8500</td></tr></table>"""
        self.assertFalse(parse_sea_rates(html))

    def test_wrong_route_is_not_rebranded_long_beach(self):
        html = """<table><tr><td>Busan</td><td>Hamburg</td>
        <td>2026</td><td>10</td><td>3800</td><td>4100</td></tr></table>"""
        self.assertFalse(parse_sea_rates(html))

    def test_live_failure_keeps_proven_snapshot_with_stale_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'kita.json'
            def inaccessible():
                raise ConnectionError('timed out')
            data = update(path, fetch_html=inaccessible)
            saved=json.loads(path.read_text(encoding='utf-8'))
            self.assertFalse(data['latest_access_ok'])
            self.assertEqual(data['latest_month'],'2026-10')
            self.assertEqual(saved['sea_routes'][-1]['feu_usd'],8500)
            self.assertIn('snapshot',saved['sea_routes'][-1]['source_type'].lower())
            self.assertEqual(saved['air_routes'],[])
            self.assertTrue(saved['errors'])


    def test_east_and_west_ports_from_primary_table(self):
        html="""<table>
        <tr><td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td><td>6700 300</td><td>8500 600</td></tr>
        <tr><td>Busan</td><td>New York</td><td>2026</td><td>10</td><td>9500 300</td><td>11900 600</td></tr>
        </table>"""
        rows=parse_sea_rates(html)
        self.assertEqual({r['destination'] for r in rows},{'New York','Long Beach'})
        self.assertEqual([r for r in rows if r['destination']=='New York'][0]['feu_usd'],11900)

    def test_archive_bulletin_parses_only_sea_export(self):
        sample="""<html><body><h1>2026년 7월 RADIS 참고 운임 안내 (해상 수출운임)</h1>
        <table><tr><th>도착지</th><th>TEU</th><th>FEU</th></tr>
        <tr><td>Long Beach</td><td>6,000</td><td>7,550</td></tr>
        <tr><td>New York</td><td>7,500</td><td>9,500</td></tr></table></body></html>"""
        url='https://www.kita.net/shippers/board/courseTrendView.do?dataSeq=3394&morgueCode=8'
        rows=parse_sea_bulletin(sample,url)
        self.assertEqual(len(rows),2)
        east=next(r for r in rows if r['destination']=='New York')
        self.assertEqual(east['feu_usd'],9500)
        self.assertEqual(east['teu_usd'],7500)
        self.assertEqual(east['source_type'],'KITA_RADIS_OFFICIAL_BULLETIN')
        self.assertEqual(parse_sea_bulletin(
           sample.replace('해상 수출운임','항공 수출운임'),url),[])

    def test_east_latest_is_marked_secondary_unless_directly_verified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'data.json'
            out=update(path,fetch_html=lambda:('<table><tr>'
               '<td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td>'
               '<td>6700 300</td><td>8500 600</td></tr></table>'))
            self.assertEqual(out['west_latest_month'],'2026-10')
            self.assertEqual(out['east_latest_month'],'2026-10')
            self.assertFalse(out['east_latest_primary_verified'])
            east=[x for x in out['sea_routes'] if x['destination']=='New York']
            self.assertIsNone(east[-1]['teu_usd'])
            self.assertIn('SECONDARY',east[-1]['source_type'])

    def test_missing_east_months_not_interpolated(self):
        with tempfile.TemporaryDirectory() as tmp:
            d=update(Path(tmp)/'data.json',fetch_html=lambda:('<table><tr>'
               '<td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td>'
               '<td>6700</td><td>8500</td></tr></table>'))
            east={x['month'] for x in d['sea_routes'] if x['destination']=='New York'}
            self.assertNotIn('2026-08',east)
            self.assertIn('2026-06',east)


    def test_secondary_new_month_is_never_called_official_kita(self):
        snippet="""<div>해상 노선 모니터</div>
        <section>🚢 부산 → 뉴욕 $12,200/FEU ▲ +2.5% 2026-11</section>
        <footer>출처 KITA 해상운임</footer>"""
        parsed=parse_secondary_east(snippet)
        self.assertEqual(parsed['feu_usd'],12200)
        self.assertIsNone(parsed['teu_usd'])
        self.assertEqual(parsed['month'],'2026-11')
        self.assertIn('SECONDARY',parsed['source_type'])
        with tempfile.TemporaryDirectory() as tmp:
            records=update(Path(tmp)/'data.json',
                fetch_html=lambda:('<table><tr>'
                   '<td>Busan</td><td>Long Beach</td><td>2026</td><td>10</td>'
                   '<td>6700</td><td>8500</td></tr></table>'),
                fetch_secondary=lambda:snippet)
            east=[r for r in records['sea_routes'] if r['destination']=='New York']
            self.assertEqual(east[-1]['month'],'2026-11')
            self.assertFalse(records['east_latest_primary_verified'])
            self.assertTrue(records['east_secondary_access_ok'])

    def test_secondary_bad_or_future_quote_is_not_backfilled(self):
        self.assertIsNone(parse_secondary_east(
            '<div>부산 → 뉴욕 $14,000/FEU 2027-01 KITA 해상운임</div>'))
        self.assertIsNone(parse_secondary_east(
            '<div>부산 → 뉴욕 $14,000/FEU 2026-10</div>'))


if __name__ == '__main__':
    unittest.main()
