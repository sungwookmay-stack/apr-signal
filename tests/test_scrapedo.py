import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import scrapedo_bestsellers as sd
from scrapedo_bestsellers import FreeQuota, normalize_page, parsed_pdp, track_scrapedo
from top100_tracker import make_snapshot


def asin(n):
    return 'B' + str(n).zfill(9)


def payload(page):
    start = 1 if page == 1 else 51
    return {
        'category': 'beauty', 'type': 'bestsellers', 'page': page,
        'ranking': [
            {'rank': i, 'asin': asin(i), 'url': 'https://www.amazon.co.uk/dp/' + asin(i)}
            for i in range(start, start + 50)
        ],
        'products': [
            {'rank': i, 'asin': asin(i),
             'title': ('medicube PDRN serum ' if i in (2, 21, 65, 77)
                       else 'ordinary beauty product ') + str(i)}
            for i in range(start, start + 30)
        ]
    }


class FakeQuota:
    def __init__(self):
        self.day = dt.date(2026, 11, 6)
        self.token = 'mock'
        self.errors = []
        self.stats = {'reserved_credits': 18}
        self.calls = []
        self.pdp_calls = []

    def can_call(self):
        return True

    def get(self, code, page, category='beauty'):
        self.calls.append((code, page, category))
        return payload(page)

    def get_pdp(self, code, product_asin):
        self.pdp_calls.append((code, product_asin))
        return {'status': 'success', 'asin': product_asin,
                'name': 'Medicube verified cosmetic', 'brand': 'medicube',
                'best_seller_rankings': [
                    {'category': 'Beauty', 'rank': 215},
                    {'category': 'Face Serums', 'rank': 8}]}


class StubResponse:
    def __init__(self, headers, data):
        self.headers = headers
        self.data = json.dumps(data).encode('utf-8')

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data


class ScrapeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        patches = [
            patch.object(sd, 'STATE', root / 'usage.json'),
            patch.object(sd, 'IDENTITY', root / 'identities.json'),
            patch.object(sd, 'PDP_STATE', root / 'pdp.json'),
            patch.object(sd, 'PDP_CHECKS', root / 'pdp_checks.json'),
            patch.object(sd, 'DIAGNOSTICS', root / 'diagnostics.json')
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def test_ranking_100_with_only_60_titles_is_not_exact_brand_count(self):
        p1, p2 = normalize_page(payload(1), 1), normalize_page(payload(2), 2)
        self.assertEqual(len(p1), 50)
        self.assertEqual(len(p2), 50)
        snap = make_snapshot('GB', [p1, p2], '2026-11-06')
        self.assertEqual(snap['coverage_count'], 100)
        self.assertTrue(snap['rank_coverage_complete'])
        self.assertFalse(snap['coverage_complete'])
        self.assertEqual(snap['identity_coverage_count'], 60)
        self.assertEqual(snap['unidentified_count'], 40)
        self.assertEqual(snap['medicube_confirmed_count'], 4)

    def test_known_verified_asin_can_fill_rank_only_slot(self):
        known = {asin(45): {'title': 'medicube official PDRN pad', 'brand': 'Medicube'}}
        page = normalize_page(payload(1), 1, known)
        self.assertEqual(page[44][2], 'medicube official PDRN pad')
        self.assertEqual(page[44][4], 'Medicube')

    def test_identity_diagnostics_distinguish_cards_cache_and_invalid_rows(self):
        data = payload(1)
        data['products'][0]['title'] = ''
        data['ranking'].append({'rank': 101, 'asin': asin(101)})
        diag = {}
        rows = normalize_page(data, 1, {asin(31): {'title': 'cached'}}, diagnostics=diag)
        self.assertEqual(len(rows), 50)
        self.assertEqual(diag['product_cards'], 30)
        self.assertEqual(diag['card_identity_rows'], 29)
        self.assertEqual(diag['missing_card_rows'], 20)
        self.assertEqual(diag['empty_card_identity_rows'], 1)
        self.assertEqual(diag['cached_identity_rows'], 1)
        self.assertEqual(diag['unresolved_rows'], 20)
        self.assertEqual(diag['rejected_rank_rows'], 1)

    def test_strategy_upgrade_never_adds_same_day_pdp_calls(self):
        fake = FakeQuota()
        fake.stats.update(last_pdp_day=fake.day.isoformat(), pdp_strategy_version=2)
        track_scrapedo('test', {'markets': [{'code': 'US', 'amazon': 'amazon.com'}]}, [], client=fake)
        self.assertEqual(fake.pdp_calls, [])

    def test_diagnostics_retain_no_raw_strings_and_work_on_all_failed_pages(self):
        fake = FakeQuota()
        fake.get = lambda *args: {'category': 'wrong-secret-value', 'token': 'private-token', 'html': 'private-body'}
        rows, notes, added, _ = track_scrapedo('test', {'markets': [{'code': 'US', 'amazon': 'amazon.com'}]}, [], client=fake)
        self.assertEqual(added, 0)
        saved = json.loads(Path(sd.DIAGNOSTICS).read_text())
        self.assertEqual(len(saved['markets']['US']['pages']), 2)
        self.assertEqual(saved['markets']['US']['pages'][0]['validation_reason'], 'category_mismatch')
        self.assertNotIn('private', json.dumps(saved))
        self.assertNotIn('wrong-secret-value', json.dumps(saved))

    def test_diagnostics_write_failure_does_not_break_collection(self):
        original = sd.save_json
        def save(path, value):
            if path == sd.DIAGNOSTICS:
                raise OSError('fixture denied')
            return original(path, value)
        with patch.object(sd, 'save_json', side_effect=save):
            rows, notes, added, _ = track_scrapedo('test', {'markets': [{'code': 'US', 'amazon': 'amazon.com'}]}, [], client=FakeQuota())
        self.assertEqual(added, 1)
        self.assertTrue(any('진단 메타데이터 저장 실패' in x for x in notes))

    def test_wrong_category_and_page_rejected(self):
        p = payload(1)
        p['category'] = 'home'
        self.assertIsNone(normalize_page(p, 1))
        self.assertIsNone(normalize_page(payload(1), 2))

    def test_all_markets_daily_and_idempotent(self):
        fake = FakeQuota()
        codes = [('US', 'com'), ('GB', 'co.uk'), ('DE', 'de'),
                 ('FR', 'fr'), ('IT', 'it'), ('ES', 'es'),
                 ('CA', 'ca'), ('JP', 'co.jp'), ('AE', 'ae'),
                 ('SA', 'sa'), ('EG', 'eg')]
        cfg = {'markets': [
            {'code': cc, 'amazon': 'amazon.' + dom} for cc, dom in codes]}
        rows, status, n, credits = track_scrapedo('test', cfg, [], client=fake)
        self.assertEqual(n, 11)
        self.assertEqual(len(fake.calls), 22)
        self.assertEqual(len(fake.pdp_calls), 4)
        self.assertEqual(sum(p not in {asin(2), asin(21), asin(65), asin(77)} for _,p in fake.pdp_calls), 2)
        self.assertTrue(all('identity_diagnostics' in x for x in rows))
        self.assertEqual(sum(x['identity_coverage_count'] for x in rows), 11 * 60 + 2)
        self.assertGreaterEqual(sum(p in {asin(2), asin(21), asin(65), asin(77)}
                                    for _,p in fake.pdp_calls), 2,
                                'PDP calls should prioritize confirmed Medicube products')
        self.assertEqual({x['country'] for x in rows}, {cc for cc, _ in codes})
        self.assertTrue(all(x['coverage_count'] == 100 for x in rows))
        self.assertTrue(all(not x['coverage_complete'] for x in rows))
        self.assertTrue(Path(sd.IDENTITY).exists())
        self.assertTrue(Path(sd.PDP_STATE).exists())
        self.assertGreater(len(json.loads(Path(sd.PDP_STATE).read_text())), 0)
        self.assertEqual(len(json.loads(Path(sd.PDP_CHECKS).read_text())), 4)
        self.assertEqual(fake.stats['pdp_strategy_version'], 3)
        rows2, notes, n2, _ = track_scrapedo('test', cfg, rows, client=fake)
        self.assertEqual(n2, 0)
        self.assertEqual(len(fake.calls), 22)
        self.assertEqual(len(fake.pdp_calls), 4)

    def test_brazil_scrapedo_market_uses_own_domain(self):
        fake=FakeQuota()
        cfg={'markets':[{'code':'BR','amazon':'amazon.com.br',
                          'amazon_beauty_slug':'beauty'}]}
        rows,notes,n,_=track_scrapedo('test',cfg,[],client=fake)
        self.assertEqual(n,1)
        self.assertEqual(len(fake.calls),2)
        self.assertEqual(rows[0]['marketplace'],'amazon.com.br')
        self.assertEqual(rows[0]['coverage_count'],100)
        self.assertFalse(rows[0]['coverage_complete'])
        self.assertTrue(all(x[0]=='BR' for x in fake.calls))
        identity,obs=parsed_pdp({'status':'success','asin':asin(2),
            'name':'medicube PDRN cream','brand':'medicube',
            'best_seller_rankings':[{'category':'Beauty','rank':21}]},
            'BR',asin(2),'2026-11-06')
        self.assertEqual(obs[0]['source_url'],
                         'https://www.amazon.com.br/dp/'+asin(2))
    def test_brand_check_negative_does_not_create_fake_bsr(self):
        ident, obs = parsed_pdp({
            'asin': asin(45), 'name': 'Compatible with Medicube Device',
            'brand': 'Generic', 'best_seller_rankings': [
                {'category': 'Beauty', 'rank': 900}]}, 'US', asin(45), '2026-11-06')
        self.assertIsNotNone(ident)
        self.assertEqual(obs, [])

    def test_pdp_category_rank_is_saved_separately(self):
        ident, obs = parsed_pdp({
            'asin': asin(45), 'brand': 'Medicube', 'name': 'Medicube mask',
            'best_seller_rankings': [
                {'category': 'Beauty', 'rank': 145},
                {'category': 'Skin Care', 'rank': 5}
            ]}, 'GB', asin(45), '2026-11-06')
        self.assertEqual(ident['brand'], 'Medicube')
        self.assertEqual([v['bsr'] for v in obs], [145, 5])
        self.assertTrue(all(x['source_quality'] == 'verified_product_rank' for x in obs))

    def test_reported_one_credit_reconciles_conservative_reservation(self):
        quota = FreeQuota('private-token', dt.date(2026, 11, 6))
        with patch.object(sd.urllib.request, 'urlopen',
                          return_value=StubResponse(
                              {'Scrape.do-Request-Cost': '1',
                               'Scrape.do-Remaining-Credits': '850'}, payload(1))):
            response = quota.get('GB', 1)
        self.assertIsInstance(response, dict)
        self.assertEqual(quota.stats['reserved_credits'], 1)
        self.assertTrue(quota.can_call())
        self.assertEqual(quota.stats['provider_credits_reported'], 1)

    def test_unexpected_cost_stops_requests_before_spending_more(self):
        quota = FreeQuota('private-token', dt.date(2026, 11, 6))
        with patch.object(sd.urllib.request, 'urlopen',
                          return_value=StubResponse(
                              {'Scrape.do-Request-Cost': '10'}, payload(1))):
            quota.get('GB', 1)
        self.assertEqual(quota.stats['reserved_credits'], 10)
        self.assertFalse(quota.can_call())
        self.assertTrue(quota.stats['pricing_mismatch'])

    def test_missing_cost_header_keeps_three_credit_reservation(self):
        quota = FreeQuota('private-token', dt.date(2026, 11, 6))
        with patch.object(sd.urllib.request, 'urlopen',
                          return_value=StubResponse({}, payload(1))):
            quota.get('GB', 1)
        self.assertEqual(quota.stats['reserved_credits'], 3)
        self.assertTrue(quota.can_call())


if __name__ == '__main__':
    unittest.main()
