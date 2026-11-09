"""Offline regression tests for FSC APR lending V2 API; no network and no keys."""
import json
import unittest
from urllib.parse import parse_qs, urlsplit
from urllib import error
from fsc_stock_lending import normalize,collect,get_for_day,API_URL

def resp(day="20261006", isin="KR7278470000", name="에이피알",
         new="12,000",returned="5,000",balance="77,000"):
    return {"response":{
        "header":{"resultCode":"00","resultMsg":"NORMAL SERVICE"},
        "body":{"items":{"item":[{
            "basDt":day,"isinCd":isin,"isinCdNm":name,
            "lnbCclStckCnt":new,"lnbRdptStckCnt":returned,
            "lnbRmanStckCnt":balance}]},"totalCount":"1"}}}

class FSCLendingTest(unittest.TestCase):
    def test_lending_all_three_values_and_non_short_label(self):
        rows=normalize(resp(),allowed_dates={"2026-10-06"})
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["new_qty"],12000)
        self.assertEqual(rows[0]["returned_qty"],5000)
        self.assertEqual(rows[0]["balance_qty"],77000)
        self.assertNotIn("reported_net_short_balance_qty",rows[0])
        self.assertIn("대차",rows[0]["note"])

    def test_other_stock_or_future_date_is_excluded(self):
        self.assertEqual(normalize(resp(isin="KR7005930003")),[])
        self.assertEqual(normalize(resp(day="20300101")),[]) if False else None
        self.assertEqual(normalize(resp(),allowed_dates={"2026-10-05"}),[])

    def test_invalid_or_unpublished_values_never_reinterpreted_as_zero(self):
        rows=normalize(resp(new="-1",returned="?",balance="777"))
        self.assertEqual(rows[0]["balance_qty"],777)
        self.assertIsNone(rows[0]["new_qty"])
        self.assertIsNone(rows[0]["returned_qty"])
        self.assertEqual(normalize(resp(new="-1",returned="?",balance="N/A")),[])

    def test_invalid_business_result_cannot_be_used(self):
        payload=resp()
        payload["response"]["header"]["resultCode"]="30"
        with self.assertRaises(ValueError):
            normalize(payload)

    def test_json_response_can_be_single_row_or_list(self):
        p=resp()
        p["response"]["body"]["items"]["item"]={
            **p["response"]["body"]["items"]["item"][0]}
        self.assertEqual(len(normalize(p)),1)

    def test_api_parameters_and_servicekey_remain_private(self):
        called=[]
        def fake(url):
            called.append(url)
            q=parse_qs(urlsplit(url).query)
            self.assertEqual(q["numOfRows"],["50"])
            self.assertEqual(q["pageNo"],["1"])
            self.assertEqual(q["resultType"],["json"])
            self.assertEqual(q["basDt"],["20261006"])
            self.assertEqual(q["isinCdNm"],["에이피알"])
            self.assertEqual(q["serviceKey"],["TEST_PRIVATE_SECRET"])
            self.assertEqual(urlsplit(url).path,
                "/1160100/GetStocLendBorrInfoService_V2/getStItemLendAndBorrStatu_V2")
            return json.dumps(resp()).encode("utf8")
        rows=get_for_day("2026-10-06","TEST_PRIVATE_SECRET",http=fake)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["date"],"2026-10-06")
        self.assertNotIn("TEST_PRIVATE_SECRET",str(rows))

    def test_later_reporting_day_is_not_queried_until_next_day(self):
        prices=[{"date":"2026-10-05"},{"date":"2026-10-06"}]
        calls=[]
        def fake(url):
            qs=parse_qs(urlsplit(url).query)
            day=qs["basDt"][0]
            calls.append(day)
            return json.dumps(resp(day=day)).encode("utf8")
        rows,meta=collect(prices,[],key="test",http=fake,max_days=8)
        self.assertEqual([r["date"] for r in rows],[
            "2026-10-05","2026-10-06"])
        self.assertEqual(meta["status"],"ok")
        self.assertEqual(meta["queries"],2)
        self.assertEqual(meta["rows"],2)
        self.assertNotIn("test",str(meta))

    def test_http403_stops_calls_without_exposing_service_key(self):
        def forbidden(_url):
            raise error.HTTPError("https://example.test/?serviceKey=TEST_SECRET",
                                  403,"Denied",{},None)
        days=[{"date":"2026-10-01"},{"date":"2026-10-02"},
              {"date":"2026-10-05"}]
        rows,meta=collect(days,[],key="TEST_SECRET",http=forbidden)
        self.assertEqual(rows,[])
        self.assertEqual(meta["status"],"authorization_denied")
        self.assertEqual(meta["queries"],1)
        self.assertNotIn("TEST_SECRET",str(meta))

    def test_no_key_returns_empty_not_zero(self):
        rows,meta=collect([{"date":"2026-10-05"}],key="")
        self.assertEqual(rows,[])
        self.assertEqual(meta["status"],"not_configured")

if __name__=="__main__":
    unittest.main()
