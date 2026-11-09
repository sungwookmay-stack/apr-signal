"""Offline test KIS read-only stock short-selling data for APR (no real keys)."""
import datetime as dt
import unittest
from urllib.parse import parse_qs, urlsplit
from kis_short_sales import (
    normalize, collect, month_windows, token, TOKEN_URL, SHORT_URL, TR_ID
)

class KISDailyShortTests(unittest.TestCase):
    def test_short_shares_and_reportable_short_balances_differ(self):
        doc={"rt_cd":"0","output2":[{
          "stck_bsop_date":"20261109","ssts_cntg_qty":"1,250",
          "acml_vol":"50,000","ssts_tr_pbmn":"500000000",
          "acml_ssts_cntg_qty":"9999999","ssts_vol_rlim":"5.0"
        }]}
        rows=normalize(doc,allowed_days={"2026-11-09"})
        self.assertEqual(rows[0]["short_trade_qty"],1250)
        self.assertEqual(rows[0]["total_traded_qty"],50000)
        self.assertEqual(rows[0]["short_volume_ratio_pct"],2.5)
        self.assertIsNone(rows[0]["reported_net_short_balance_qty"])
        self.assertIsNone(rows[0]["short_trade_value_krw"])
        self.assertIsNone(rows[0]["short_value_ratio_pct"])
        self.assertNotIn("acml_ssts_cntg_qty",rows[0])

    def test_bad_or_untrusted_rows_not_numeric_zero(self):
        self.assertEqual(normalize({"rt_cd":"1","output2":[]}),[])
        self.assertEqual(normalize({"rt_cd":"0","output2":{}}),[])
        examples=[
          {"stck_bsop_date":"20261109","ssts_cntg_qty":"?","acml_vol":"100"},
          {"stck_bsop_date":"20261109","ssts_cntg_qty":"300","acml_vol":"100"},
          {"stck_bsop_date":"20261109","ssts_cntg_qty":"0","acml_vol":None},
          {"stck_bsop_date":"20301109","ssts_cntg_qty":"30","acml_vol":"100"},
          {"stck_bsop_date":"20261106","ssts_cntg_qty":"30","acml_vol":"100"}
        ]
        self.assertEqual(normalize({"rt_cd":"0","output2":examples},
                        allowed_days={"2026-11-09"}),[])

    def test_missing_keys_do_not_call_http(self):
        def never(*a,**kw):
            raise AssertionError("No network without key pair")
        rows,meta=collect([{"date":"2026-11-09"}],
                          key="",secret="",http=never)
        self.assertEqual(rows,[])
        self.assertEqual(meta["status"],"not_configured")

    def test_month_windows_bound_and_order(self):
        ranges=month_windows("2026-09-15","2026-11-09",max_windows=3)
        self.assertEqual(ranges,[
           ("20260915","20260930"),("20261001","20261031"),
           ("20261101","20261109")])

    def test_read_only_oauth_and_monthly_short_query(self):
        calls=[]
        def fake(url,method="GET",headers=None,data=None):
            calls.append((url,method,headers,data))
            if url==TOKEN_URL:
                self.assertEqual(method,"POST")
                self.assertEqual(data["grant_type"],"client_credentials")
                self.assertEqual(data["appkey"],"APPKEY")
                self.assertEqual(data["appsecret"],"SECRETPAIR")
                return {"access_token":"MOCKTOKEN_LONG"}
            self.assertEqual(method,"GET")
            self.assertEqual(urlsplit(url).path,
                             "/uapi/domestic-stock/v1/quotations/daily-short-sale")
            q=parse_qs(urlsplit(url).query)
            self.assertEqual(q["FID_INPUT_ISCD"],["278470"])
            self.assertEqual(q["FID_COND_MRKT_DIV_CODE"],["J"])
            self.assertEqual(headers["tr_id"],"FHPST04830000")
            self.assertEqual(headers["authorization"],"Bearer MOCKTOKEN_LONG")
            return {"rt_cd":"0","output2":[{
                "stck_bsop_date":"20261109",
                "ssts_cntg_qty":"1,000","acml_vol":"200,000"}]}
        prices=[{"date":"2026-11-09"}]
        result,meta=collect(prices,key="APPKEY",secret="SECRETPAIR",http=fake)
        self.assertEqual(result[0]["short_volume_ratio_pct"],0.5)
        self.assertEqual(meta["status"],"ok")
        self.assertEqual(meta["rows"],1)
        self.assertEqual(len(calls),2)
        self.assertNotIn("SECRETPAIR",str(meta))
        self.assertNotIn("MOCKTOKEN",str(meta))
        self.assertNotIn("SECRETPAIR",str(result))

    def test_token_failure_does_not_leak_response_secret(self):
        def fake(url,method="GET",headers=None,data=None):
            return {"msg1":"SECRETPAIR unauthorized"}
        with self.assertRaises(RuntimeError) as err:
            token("APPKEY","SECRETPAIR",http=fake)
        self.assertNotIn("SECRETPAIR",str(err.exception))

    def test_failure_does_not_claim_healthy_trading_feed(self):
        def fake(url,method="GET",headers=None,data=None):
            if url==TOKEN_URL:
                return {"access_token":"MOCKTOKEN_LONG"}
            return {"rt_cd":"1","msg1":"API_BLOCKED"}
        arr,meta=collect([{"date":"2026-11-09"}],
                         key="APPKEY",secret="SECRETPAIR",http=fake)
        self.assertEqual(arr,[])
        self.assertEqual(meta["status"],"unavailable")
        self.assertNotIn("API_BLOCKED",str(meta))


if __name__=="__main__":
    unittest.main()
