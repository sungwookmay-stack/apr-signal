"""Offline, no-secret tests of public Naver KRX investor SHARES and pagination."""
import datetime as dt
import json
import unittest

from naver_public_flows import normalize, get_page, collect
from flows_engine import evaluate


def item(day, foreign=10, institution=-3, personal=-7):
    return {
        "localTradedAt":day,
        "krx":{
            "foreignNetVolume":str(foreign),
            "foreignBuyVolume":str(max(0,foreign)+20),
            "foreignSellVolume":str(max(0,-foreign)+20),
            "organizationNetVolume":str(institution),
            "organizationBuyVolume":str(max(0,institution)+20),
            "organizationSellVolume":str(max(0,-institution)+20),
            "individualNetVolume":str(personal),
            "individualBuyVolume":str(max(0,personal)+20),
            "individualSellVolume":str(max(0,-personal)+20),
            "closingPrice":"243500","tradingVolume":"310069"
        },
        "nxt":{"foreignNetVolume":"999999"}
    }


def response(items, more=False, cursor=None):
    return {"isSuccess":True,"result":{
        "items":items,"hasNext":more,"cursor":cursor}}


class NaverPublicFlowsTest(unittest.TestCase):
    def test_primary_data_is_shares_not_investor_cash(self):
        data=normalize(response([item('2026-11-06',foreign=10,
                                     institution=-3,personal=-7)]))
        self.assertEqual(len(data),1)
        row=data[0]
        self.assertEqual(row['foreign_net_qty'],10)
        self.assertEqual(row['foreign'],10*243500)
        self.assertEqual(row['institution'],-3*243500)
        self.assertEqual(row['individual'],-7*243500)
        self.assertIsNone(row['pension'])
        self.assertEqual(row['market_scope'],'KRX_ONLY_NOT_NXT')
        self.assertEqual(row['unit'],'KRW_ESTIMATED_NOT_ACTUAL')
        self.assertTrue(row['amount_estimated'])
        self.assertIn('KRX',row['source'])

    def test_any_missing_or_inconsistent_actor_is_missing_not_zero(self):
        r=item('2026-11-06')
        r['krx']['foreignNetVolume']='999'
        r['krx']['organizationNetVolume']='N/A'
        r['krx']['individualNetVolume']='0'
        r['krx']['individualBuyVolume']='11'
        r['krx']['individualSellVolume']='11'
        d=normalize(response([r]))[0]
        self.assertIsNone(d['foreign'])
        self.assertIsNone(d['institution'])
        self.assertEqual(d['individual'],0)

    def test_stale_or_future_rows_skipped(self):
        r=item('2030-01-01')
        self.assertEqual(normalize(response([r])),[])
        self.assertEqual(
            normalize(response([item('2026-11-06')]),
                      latest_date='2026-11-05'),[])

    def test_malformed_or_unavailable_does_not_create_false_records(self):
        self.assertEqual(normalize(None),[])
        self.assertEqual(normalize({"isSuccess":False,"result":{}}),[])
        self.assertEqual(normalize({"isSuccess":True,"result":{"items":{}}}),[])
        p=item('2026-11-06')
        p['krx']['closingPrice']=None
        self.assertEqual(normalize(response([p])),[])

    def test_opaque_cursor_pagination_and_no_duplicate_days(self):
        dates=['2026-11-06','2026-11-05','2026-11-04',
               '2026-11-03','2026-11-02','2026-10-30']
        seen=[]
        def fake(url,timeout):
            seen.append(url)
            if 'cursor=opaque1' in url:
                doc=response([item(d) for d in dates[3:]],
                             more=False,cursor=None)
            else:
                doc=response([item(d) for d in dates[:3]],
                             more=True,cursor='opaque1')
            return json.dumps(doc).encode()
        rows,st=collect('2026-11-06',get_bytes=fake,max_pages=6)
        self.assertEqual(len(rows),6)
        self.assertEqual(st['pages'],2)
        self.assertTrue(st['has_full_history'])
        self.assertEqual(rows[0]['date'],'2026-10-30')
        self.assertEqual(rows[-1]['date'],'2026-11-06')
        self.assertIn('cursor=opaque1',seen[1])
        self.assertIn('code=278470',seen[0])

    def test_expired_cursor_does_not_loop_forever(self):
        def fake(url,timeout):
            return json.dumps(response(
                [item('2026-11-06')],more=True,cursor='same')).encode()
        rows,st=collect('2026-11-06',get_bytes=fake,max_pages=9)
        self.assertEqual(len(rows),1)
        self.assertEqual(st['pages'],2)
        self.assertEqual(st['status'],'partial')
        self.assertTrue(st['issues'])

    def test_approximate_month_results_are_not_confirmed_cash(self):
        base=dt.date(2026,8,1)
        dates=[(base+dt.timedelta(days=i)).isoformat() for i in range(80)]
        prices=[{"date":d,"close_krw":243500,"volume":100000} for d in dates]
        samples=normalize(response([item(d) for d in dates]),latest_date=dates[-1])
        analysis=evaluate(prices,samples)
        w=analysis['actors']['foreign']['windows']['20']
        self.assertEqual(w['estimated_value_days'],20)
        self.assertEqual(w['net_qty_shares'],200)
        self.assertEqual(analysis['combined']['value_basis'],
                         'closing_price_times_net_shares_estimate')
        self.assertNotEqual(analysis['combined']['level'],'strong')
        self.assertIsNone(analysis['actors']['pension']['score'])


if __name__=="__main__":
    unittest.main()
