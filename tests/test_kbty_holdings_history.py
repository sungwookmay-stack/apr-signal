import json
import unittest
from unittest.mock import patch

import build_data
from kbty_official import parse_official


def table(date, value, px, shares=86):
    return ("<h3>KBTY Top 10 Holdings</h3><time>as of "+date+"</time>"
            "<caption>KBTY holdings as of "+date+", largest first.</caption>"
            "<tr><td>5.89%</td><td>A278470</td><td>APR CORP/KOREA</td><td>COMMON STOCK</td>"
            f"<td>{px}</td><td>{shares:,}</td><td>{value}</td><td>Y0R9CJ118</td></tr>")


class OfficialHoldingsHistory(unittest.TestCase):
    def test_tables_not_display_order_or_caption_duplicates(self):
        page=table('11/17/2026','14,844.21','172.61')+table('11/18/2026','15,159.58','176.27')
        out=parse_official(page)
        self.assertEqual([(x['as_of'],x['shares']) for x in out['issuer_apr_history']],
                         [('2026-11-17',86),('2026-11-18',86)])
        self.assertEqual(out['issuer_apr']['market_value_usd'],15159.58)

    def test_market_value_sanity_and_same_date_conflict(self):
        page=table('11/17/2026','14,844.21','172.61')
        page+=table('11/18/2026','151.58','176.27')
        page+=table('11/17/2026','15,016.75','172.61',87)
        self.assertNotIn('issuer_apr_history',parse_official(page))

    def test_seed_live_and_preserved_history_no_synthetic_zero(self):
        source=build_data.ROOT/'config/kbty_issuer_snapshot.json'
        seed=json.loads(source.read_text())
        # Keep the test's dated fixture independent of later issuer seed refreshes.
        seed['apr_holdings_history']=[r for r in seed['apr_holdings_history'] if r['as_of'] in ('2026-11-17','2026-11-18')]
        previous={'apr_holdings_history':[
            {**seed['apr_holdings_history'][0], 'as_of':'2026-11-16'},
        ]}
        def read(path, default):
            return seed if str(path).endswith('kbty_issuer_snapshot.json') else previous
        with patch.object(build_data,'read_json',side_effect=read), patch.object(build_data,'load_csv',return_value=[]), patch.object(build_data,'save'):
            no_live=build_data.collect_kbty(offline_snapshot=True)
        self.assertEqual([x['as_of'] for x in no_live['apr_holdings_history']],['2026-11-16','2026-11-17','2026-11-18'])
        self.assertEqual(no_live['apr_shares'],86)
        self.assertNotIn('fund_shares_outstanding',no_live)
