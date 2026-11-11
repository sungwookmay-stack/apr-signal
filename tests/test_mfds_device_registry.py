"""Synthetic registry fixtures only: no real APR permit is asserted."""
import copy
import json
import unittest
from urllib import error, parse
from mfds_device_registry import (normalize, parse_page, fetch_company,
                                  update_snapshot, RegistryError, API_URL)


def row(**kw):
    return dict(MDEQ_PRDLST_SN="fixture-1", ENTRPS="주식회사 에이피알",
                BRNO="220-88-89441", PRDUCT="TEST ONLY", GRADE="4",
                PRDUCT_PRMISN_NO="FIXTURE-NOT-A-PERMIT", PRMISN_DT="20200101",
                CHG_DT="20260101", **kw)


def payload(rows=None, total=None):
    rows = [row()] if rows is None else rows
    return {"response": {"header": {"resultCode": "00"}, "body": {
        "items": {"item": rows}, "totalCount": len(rows) if total is None else total}}}


def mock(rows=None):
    def http(_):
        return json.dumps(payload(rows)).encode()
    return http


class MFDSRegistryTests(unittest.TestCase):
    def test_no_key_no_request_not_no_permits(self):
        def fail(_): self.fail("network without key")
        out = update_snapshot(key="", http=fail)
        self.assertEqual(out["status"], "not_configured")
        self.assertIsNone(out["observed_count"])
        self.assertIsNone(out["last_success_at"])

    def test_no_automatic_domestic_claim_from_korean_registry(self):
        out = normalize(row())
        self.assertEqual(out["company_match"], "public_business_number")
        self.assertEqual(out["domestic_market_authorization"], "not_verified")
        self.assertEqual(out["export_scope"], "not_verified")
        self.assertNotIn("approved", out)

    def test_similar_company_and_product_names_not_confirmed(self):
        r = row(); r.update(ENTRPS="에이피알파트너스", BRNO="9999999999",
                            PRDUCT="AGE-R")
        self.assertEqual(normalize(r)["company_match"], "candidate_requires_review")
        r.update(ENTRPS="(주) 에이피알팩토리", BRNO="")
        self.assertEqual(normalize(r)["company_match"],
                         "exact_company_name_requires_initial_identity_review")

    def test_single_item_and_zero_results(self):
        p = payload(); p["response"]["body"]["items"]["item"] = row()
        self.assertEqual(len(parse_page(p)[0]), 1)
        self.assertEqual(parse_page(payload([])), ([], 0))

    def test_live_per_record_item_envelope(self):
        p = payload()
        p["response"]["body"]["items"] = [{"item": row()}]
        rows, total = parse_page(p)
        self.assertEqual(total, 1)
        self.assertEqual(rows[0]["registry_id"], "fixture-1")
        p["response"]["body"]["items"] = [{"item": {}}]
        with self.assertRaisesRegex(RegistryError, "missing_record_identity"):
            parse_page(p)

    def test_business_error_and_invalid_schema(self):
        p = payload(); p["response"]["header"]["resultCode"] = "30"
        with self.assertRaisesRegex(RegistryError, "authorization_denied"): parse_page(p)
        with self.assertRaises(RegistryError): parse_page({})
        p = payload(); p["response"]["body"].pop("totalCount")
        with self.assertRaises(RegistryError): parse_page(p)
        p = payload([{}])
        with self.assertRaises(RegistryError): parse_page(p)

    def test_pagination_complete_and_parameter_case(self):
        calls = []
        def http(url):
            self.assertTrue(url.startswith(API_URL))
            q = parse.parse_qs(parse.urlsplit(url).query)
            self.assertEqual(q["ENTRPS"], ["에이피알"])
            self.assertEqual(q["serviceKey"], ["secret+value"])
            self.assertEqual(q["type"], ["json"])
            page = int(q["pageNo"][0]); calls.append(page)
            r = row(); r["MDEQ_PRDLST_SN"] = str(page)
            return json.dumps(payload([r], 2)).encode()
        result = fetch_company("에이피알", "secret%2Bvalue", http=http)
        self.assertEqual(len(result), 2)
        self.assertEqual(calls, [1, 2])
        self.assertNotIn("secret", str(result))

    def test_duplicate_or_empty_partial_page_never_success(self):
        with self.assertRaisesRegex(RegistryError, "duplicate_page_records"):
            fetch_company("에이피알", "s", http=lambda _: json.dumps(payload(total=2)))
        with self.assertRaisesRegex(RegistryError, "incomplete_pagination"):
            fetch_company("에이피알", "s", http=lambda _: json.dumps(payload([], 1)))
        with self.assertRaisesRegex(RegistryError, "page_limit_reached"):
            fetch_company("에이피알", "s", http=lambda _: json.dumps(payload(total=2)), max_pages=1)

    def test_baseline_never_announces_old_approvals(self):
        out = update_snapshot(key="s", http=mock(), checked_at="2026-11-11")
        self.assertEqual(out["status"], "ok")
        self.assertEqual(out["observed_count"], 1)  # Aliases deduplicated.
        self.assertTrue(out["is_initial_baseline"])
        self.assertEqual(out["events"], [])
        self.assertEqual(out["event_history"], [])
        self.assertEqual(out["records"][0]["permit_date"], "20200101")

    def test_later_discovery_and_change_do_not_mean_new_approval(self):
        before = update_snapshot(key="s", http=mock([]), checked_at="day1")
        after = update_snapshot(before, key="s", http=mock(), checked_at="day2")
        self.assertEqual(after["events"][0]["kind"], "newly_observed_registry_record")
        changed = row(); changed["CHG_DT"] = "20261111"
        final = update_snapshot(after, key="s", http=mock([changed]), checked_at="day3")
        self.assertEqual(final["events"][0]["kind"], "registry_record_changed")
        self.assertEqual(len(final["event_history"]), 2)
        self.assertEqual(final["records"][0]["first_seen_at"], "day2")
        again = update_snapshot(final, key="s", http=mock([changed]), checked_at="day4")
        self.assertEqual(again["events"], [])
        self.assertEqual(len(again["event_history"]), 2)

    def test_missing_record_is_preserved_not_revoked(self):
        before = update_snapshot(key="s", http=mock(), checked_at="day1")
        after = update_snapshot(before, key="s", http=mock([]), checked_at="day2")
        self.assertEqual(len(after["records"]), 1)
        self.assertEqual(after["observed_count"], 0)
        self.assertEqual(after["events"][0]["kind"], "not_observed_requires_review")
        self.assertEqual(after["records"][0]["last_seen_at"], "day1")
        again = update_snapshot(after, key="s", http=mock([]), checked_at="day3")
        self.assertEqual(again["events"], [])

    def test_partial_failure_preserves_last_full_snapshot_without_secret(self):
        before = update_snapshot(key="s", http=mock(), checked_at="day1")
        original = copy.deepcopy(before)
        calls = []
        def http(url):
            calls.append(url)
            if len(calls) == 1: return json.dumps(payload([]))
            raise error.HTTPError(url, 403, "SECRET", {}, None)
        out = update_snapshot(before, key="PRIVATE_SECRET", http=http, checked_at="day2")
        self.assertEqual(out["status"], "authorization_denied")
        self.assertEqual(out["records"], before["records"])
        self.assertEqual(out["last_success_at"], "day1")
        self.assertFalse(out["current_scan_complete"])
        self.assertIsNone(out["observed_count"])
        self.assertEqual(out["events"], [])
        self.assertEqual(before, original)
        self.assertNotIn("SECRET", str(out))

    def test_first_authorization_failure_stops_without_retry(self):
        calls = []
        def http(url):
            calls.append(url)
            raise error.HTTPError(url, 403, "SECRET", {}, None)
        out = update_snapshot(key="PRIVATE_SECRET", http=http)
        self.assertEqual(len(calls), 1)
        self.assertEqual(out["status"], "authorization_denied")

    def test_network_error_has_no_secret_url(self):
        def http(url): raise error.URLError(url)
        out = update_snapshot(key="PRIVATE_SECRET", http=http)
        self.assertEqual(out["status"], "network_error")
        self.assertNotIn("PRIVATE_SECRET", str(out))

if __name__ == "__main__": unittest.main()
