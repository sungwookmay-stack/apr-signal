"""KITA official route parser regression tests, no live network or paid API."""
import json
import tempfile
import unittest
from pathlib import Path
from kita_rates import parse_sea_rates, update, SEA_URL


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


if __name__ == '__main__':
    unittest.main()
