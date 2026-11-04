#!/usr/bin/env python3
"""Free-first Amazon Beauty Top 100 monitoring, with optional verified PDP BSR.

Uses Scrape.do only when SCRAPEDO_TOKEN is present. Never infers an unseen
rank or assumes an unidentified ASIN is not Medicube. Country-specific
ASIN identity cache helps improve coverage without re-buying old identities.
"""
from __future__ import annotations
import datetime as dt
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from top100_tracker import make_snapshot, MEDICUBE, EXCLUSION, ASIN, is_medicube

ROOT = Path(__file__).resolve().parent
STATE = ROOT / 'data/scrapedo_usage.json'
IDENTITY = ROOT / 'data/amazon_asin_identities.json'
PDP_STATE = ROOT / 'data/scrapedo_pdp.json'
API = 'https://api.scrape.do/plugin/amazon/'
LOCAL_LIMIT = 900
RESERVE_PER_CALL = 3
MAX_PDP_DAILY = 4


def load_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return default


def save_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def identity_key(country, asin):
    return country.upper() + ':' + asin.upper()


class FreeQuota:
    """Reserve 3 credits before requests; reconcile ONLY against a verified cost header.

    Unknown/failed requests keep the conservative reservation. Unexpectedly
    expensive responses stop further calls, rather than risking a bill.
    """
    def __init__(self, token, day=None):
        self.token = token
        self.day = day or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
        self.month = self.day.strftime('%Y-%m')
        self.stats = load_json(STATE, {})
        if self.stats.get('month') != self.month:
            self.stats = {'month': self.month, 'reserved_credits': 0, 'calls': 0,
                          'provider_credits_reported': 0}
        self.errors = []

    def can_call(self):
        remaining = self.stats.get('provider_remaining_last')
        return (bool(self.token) and not self.stats.get('pricing_mismatch')
                and self.stats.get('reserved_credits', 0) + RESERVE_PER_CALL <= LOCAL_LIMIT
                and (remaining is None or remaining > 20))

    def _get(self, endpoint, parameters, label):
        if not self.can_call():
            return None
        self.stats['reserved_credits'] += RESERVE_PER_CALL
        self.stats['calls'] += 1
        self.stats['last_call_date'] = self.day.isoformat()
        save_json(STATE, self.stats)  # reserve first: repeat runs never reset spending
        params = dict(parameters, token=self.token, super='false')
        url = API + endpoint + '?' + urllib.parse.urlencode(params)
        try:
            request = urllib.request.Request(
                url, headers={'Accept': 'application/json', 'User-Agent': 'APR-SIGNAL/1.0'})
            with urllib.request.urlopen(request, timeout=32) as response:
                raw = response.read(1500000)
                cost = response.headers.get('Scrape.do-Request-Cost')
                if cost is not None:
                    try:
                        actual = int(cost)
                        if 0 <= actual <= 50:
                            self.stats['reserved_credits'] += actual - RESERVE_PER_CALL
                            self.stats['provider_credits_reported'] += actual
                            self.stats['last_verified_cost'] = actual
                            if actual > 1:
                                self.stats['pricing_mismatch'] = True
                                self.errors.append('예상 1크레딧 초과: 추가 Scrape.do 요청 중단')
                    except (TypeError, ValueError):
                        self.errors.append('Scrape.do 비용 헤더 해석 실패: 보수적 예약 유지')
                else:
                    self.errors.append('Scrape.do 비용 헤더 없음: 요청당 3크레딧 예약 유지')
                remain = response.headers.get('Scrape.do-Remaining-Credits')
                if remain is not None:
                    try:
                        self.stats['provider_remaining_last'] = int(remain)
                    except (TypeError, ValueError):
                        pass
                save_json(STATE, self.stats)
            return json.loads(raw.decode('utf-8'))
        except urllib.error.HTTPError as exc:
            # Some 4xx statuses cost credits, so keep the initial 3-credit reserve.
            self.errors.append(f'{label}: HTTP {exc.code}')
        except (TimeoutError, urllib.error.URLError, ValueError, OSError) as exc:
            # NEVER print the URL or exception body; token is in the query string.
            self.errors.append(f'{label}: {type(exc).__name__}')
        return None

    def get(self, domain, page, category='beauty'):
        return self._get('bestsellers',
                         {'category': category, 'geocode': domain.lower(),
                          'type': 'bestsellers', 'page': page},
                         f'{domain} Top100 page {page}')

    def get_pdp(self, country, asin):
        return self._get('pdp', {'asin': asin, 'geocode': country.lower()},
                         f'{country} PDP')


def _known_titles(history, verified_amazon):
    names = {}
    for snapshot in history:
        for obj in snapshot.get('medicube_listings', []):
            asin = str(obj.get('asin') or '').upper()
            title = str(obj.get('title') or '')
            if ASIN.fullmatch(asin) and MEDICUBE.search(title) and not EXCLUSION.search(title):
                names[identity_key(snapshot.get('country', ''), asin)] = {'title': title, 'brand': ''}
    for row in verified_amazon:
        asin = str(row.get('asin') or '').upper()
        title = str(row.get('title') or row.get('product') or '')
        cc = str(row.get('country') or '')
        if ASIN.fullmatch(asin) and MEDICUBE.search(title) and not EXCLUSION.search(title):
            names[identity_key(cc, asin)] = {'title': title, 'brand': ''}
    return names


def normalize_page(payload, page, known=None):
    """Join all 50 ranking rows to available product cards using exact ASIN."""
    if not isinstance(payload, dict):
        return None
    if str(payload.get('category') or '').lower() not in (
            'beauty', 'beauty-personal-care', 'beauty-and-personal-care'):
        return None
    if str(payload.get('type') or 'bestsellers').lower() not in ('bestsellers', 'best_sellers'):
        return None
    if str(payload.get('page', page)) != str(page):
        return None
    ranks, details = payload.get('ranking'), payload.get('products')
    if not isinstance(ranks, list) or not isinstance(details, list):
        return None
    known = known or {}
    by_asin = {str(p.get('asin') or '').upper(): p for p in details if isinstance(p, dict)}
    result = []
    expected = range(1, 51) if page == 1 else range(51, 101)
    for item in ranks:
        if not isinstance(item, dict):
            continue
        try:
            rank = int(item.get('rank'))
        except (ValueError, TypeError):
            continue
        asin = str(item.get('asin') or '').upper()
        if rank not in expected or not ASIN.fullmatch(asin):
            continue
        info = by_asin.get(asin, {})
        old = known.get(asin) or {}
        if isinstance(old, str):
            old = {'title': old}
        title = str(info.get('title') or old.get('title') or '')[:180]
        brand = str(info.get('brand') or old.get('brand') or '')[:100]
        # Only link to an official product page for this market.
        url = str(item.get('url') or info.get('url') or '')
        if not url.startswith('https://www.amazon.'):
            url = ''
        result.append((rank, asin, title, url, brand))
    return result


def parsed_pdp(payload, country, asin, day):
    """Return a trusted identity and optional category-specific BSR observations."""
    if not isinstance(payload, dict) or payload.get('status', 'success') != 'success':
        return None, []
    if str(payload.get('asin') or asin).upper() != asin:
        return None, []
    title = str(payload.get('name') or payload.get('title') or '').strip()[:180]
    brand = str(payload.get('brand') or '').strip()[:100]
    if not title and not brand:
        return None, []
    identity = {'title': title, 'brand': brand, 'verified_at': day, 'source': 'Scrape.do PDP'}
    if not is_medicube(identity):
        return identity, []
    seen = set()
    observations = []
    for raw in payload.get('best_seller_rankings') or []:
        if not isinstance(raw, dict):
            continue
        category = str(raw.get('category') or '').strip()[:120]
        try:
            rank = int(str(raw.get('rank') or '').replace(',', '').replace('#', ''))
        except (ValueError, TypeError):
            continue
        if not category or not 1 <= rank <= 100000000 or category in seen:
            continue
        seen.add(category)
        observations.append({
            'date': day, 'country': country, 'asin': asin,
            'product': title or brand, 'title': title, 'bsr': rank,
            'category': category, 'source': 'Scrape.do Amazon PDP',
            'source_quality': 'verified_product_rank',
            'source_url': 'https://www.amazon.' + ({
                'US':'com','GB':'co.uk','DE':'de','FR':'fr','IT':'it',
                'ES':'es','CA':'ca','JP':'co.jp','AE':'ae','SA':'sa','EG':'eg'
            }.get(country, 'com')) + '/dp/' + asin
        })
    return identity, observations


def _round_robin_candidates(candidates, codes, day):
    """Rotate markets fairly, taking the highest rank first within each market."""
    by_country = {code: [] for code in codes}
    for entry in candidates:
        by_country.setdefault(entry[0], []).append(entry)
    for group in by_country.values():
        group.sort(key=lambda obj: obj[1])
    if not codes:
        return []
    shift = day.toordinal() % len(codes)
    ordered = codes[shift:] + codes[:shift]
    output = []
    while any(by_country.values()):
        for code in ordered:
            if by_country.get(code):
                output.append(by_country[code].pop(0))
    return output


def track_scrapedo(token, config, history, verified_amazon=None, client=None):
    """Visit ALL configured Amazon markets daily, with a 900-credit fail-closed cap.

    Unknown ASINs remain unknown until card/PDP evidence resolves them.
    Four optional PDPs/day prioritize unseen brand identities, then proven
    Medicube products for category-specific BSR observations.
    """
    quota = client or FreeQuota(token)
    history = list(history or [])
    if not token:
        return history, ['SCRAPEDO_TOKEN 미등록 — 기존 API.SH 사용'], 0, 0

    today = quota.day.isoformat()
    markets = [m for m in config.get('markets', []) if m.get('amazon')]
    codes = [m['code'] for m in markets]
    names = _known_titles(history, verified_amazon or [])
    identities = load_json(IDENTITY, {})
    if not isinstance(identities, dict):
        identities = {}
    for k, v in names.items():
        identities.setdefault(k, v)
    pending = []
    notes = []
    for market in markets:
        cc = market['code']
        prior_today = next((x for x in history if x.get('date') == today
                            and x.get('country') == cc), None)
        if prior_today and str(prior_today.get('source', '')).startswith('Scrape.do'):
            notes.append(f'{cc}: 당일 Scrape.do 기록 재사용')
            continue
        known = {key.split(':', 1)[1]: record for key, record in identities.items()
                 if key.startswith(cc + ':') and isinstance(record, (dict, str))}
        pages = []
        slug = market.get('amazon_beauty_slug') or 'beauty'
        for page in (1, 2):
            if not quota.can_call():
                notes.append('Scrape.do 안전 예산·비용 확인에 따른 수집 중단')
                break
            response = quota.get(cc, page, slug)
            normalized = normalize_page(response, page, known)
            if normalized is None:
                notes.append(f'{cc}: Beauty {page}페이지 검증 실패 (카테고리 slug={slug})')
                continue
            if normalized:
                pages.append(normalized)
                # Cache full chart cards of BOTH Medicube and other brands.
                for _, asin, title, _, brand in normalized:
                    if title or brand:
                        k = identity_key(cc, asin)
                        existing = identities.get(k, {})
                        if isinstance(existing, str):
                            existing = {'title': existing}
                        if not existing.get('title') and title:
                            existing['title'] = title
                        if brand and not existing.get('brand'):
                            existing['brand'] = brand
                        existing.setdefault('source', 'Scrape.do Best Sellers card')
                        existing.setdefault('verified_at', today)
                        identities[k] = existing
        if pages:
            pending.append((market, pages, prior_today))

    # The four PDP requests per day are shared across all 11 countries.
    # We do not guess an individual rank for a product absent from a Top 100.
    if hasattr(quota, 'get_pdp') and quota.stats.get('last_pdp_day') != today:
        unknown = []
        confirmed_outside = []
        current_rank_asins = set()
        for market, pages, _ in pending:
            cc = market['code']
            for rows in pages:
                for rank, asin, title, _, brand in rows:
                    current_rank_asins.add((cc, asin))
                    if not title and not brand and identity_key(cc, asin) not in identities:
                        unknown.append((cc, rank, asin))
        for (cc, asin), row in {
            (str(r.get('country', '')), str(r.get('asin', '')).upper()): r
            for r in (verified_amazon or [])
            if ASIN.fullmatch(str(r.get('asin', '')).upper())
        }.items():
            if cc not in codes or (cc, asin) in current_rank_asins:
                continue
            if not is_medicube({'title':row.get('title') or row.get('product'),
                                'brand':row.get('brand')}):
                continue
            confirmed_outside.append((cc, 999, asin))

        # Reserve two PDP requests for off-chart confirmed Medicube when possible.
        ordered_unknown = _round_robin_candidates(unknown, codes, quota.day)
        ordered_known = _round_robin_candidates(confirmed_outside, codes, quota.day)
        selected = ordered_unknown[:2] + ordered_known[:2]
        seen = {(cc, asin) for cc, _, asin in selected}
        for candidate in ordered_unknown[2:] + ordered_known[2:]:
            if len(selected) >= MAX_PDP_DAILY:
                break
            if (candidate[0], candidate[2]) not in seen:
                selected.append(candidate)
                seen.add((candidate[0], candidate[2]))

        pdp_history = load_json(PDP_STATE, [])
        if not isinstance(pdp_history, list):
            pdp_history = []
        observed = 0
        for cc, _, asin in selected:
            if not quota.can_call():
                notes.append('PDP 조회 중단: 월 900크레딧 안전 상한')
                break
            response = quota.get_pdp(cc, asin)
            ident, observations = parsed_pdp(response, cc, asin, today)
            if ident is None:
                continue
            identities[identity_key(cc, asin)] = ident
            observed += 1
            for obs in observations:
                key = (obs['date'], obs['country'], obs['asin'], obs['category'])
                pdp_history = [p for p in pdp_history if
                    (p.get('date'), p.get('country'), p.get('asin'), p.get('category')) != key]
                pdp_history.append(obs)
        save_json(PDP_STATE, pdp_history[-2000:])
        quota.stats['last_pdp_day'] = today
        save_json(STATE, quota.stats)
        notes.append(f'PDP 상품명/BSR 확인 {observed}개 · 일일 한도 {MAX_PDP_DAILY}회')

    save_json(IDENTITY, identities)
    added = 0
    for market, pages, prior_today in pending:
        cc = market['code']
        # Refresh the in-memory cards with identities learned from PDP today.
        refreshed = []
        for page in pages:
            rebuilt = []
            for rank, asin, title, url, brand in page:
                old = identities.get(identity_key(cc, asin), {})
                if isinstance(old, str):
                    old = {'title': old}
                rebuilt.append((rank, asin, title or old.get('title', ''),
                                url, brand or old.get('brand', '')))
            refreshed.append(rebuilt)
        snapshot = make_snapshot(cc, refreshed, today)
        for product in snapshot['medicube_listings']:
            if not product.get('url'):
                product['url'] = 'https://www.' + market['amazon'] + '/dp/' + product['asin']
        snapshot['marketplace'] = market['amazon']
        snapshot['category_slug'] = market.get('amazon_beauty_slug') or 'beauty'
        snapshot['source'] = 'Scrape.do Amazon Best Sellers Beauty'
        # Confirm entry/exit ONLY when both observations resolve all 100 identities.
        prior = next((s for s in reversed(history)
                      if s.get('country') == cc and s.get('date') < today), None)
        if prior and prior.get('coverage_complete') and snapshot.get('coverage_complete'):
            a = {p['asin'] for p in prior.get('medicube_listings', [])}
            b = {p['asin'] for p in snapshot['medicube_listings']}
            snapshot['new_asins'] = sorted(b - a)
            snapshot['exit_asins'] = sorted(a - b)
            snapshot['new_count'] = len(snapshot['new_asins'])
            snapshot['exit_count'] = len(snapshot['exit_asins'])
        if prior_today:
            quality = lambda s: (s.get('coverage_count', 0), s.get('identity_coverage_count', 0))
            if quality(prior_today) >= quality(snapshot):
                notes.append(f'{cc}: 기존 기록이 동일하거나 더 완전하여 보존')
                continue
            history = [s for s in history if not (
                s.get('country') == cc and s.get('date') == today)]
        history.append(snapshot)
        added += 1
        notes.append(f"{cc}: Medicube 최소 {snapshot['medicube_confirmed_count']}종, "
                     f"순위 {snapshot['coverage_count']}/100, "
                     f"브랜드 식별 {snapshot['identity_coverage_count']}/100")
    notes.extend(quota.errors[:12])
    history.sort(key=lambda s: (s.get('date', ''), s.get('country', '')))
    return history[-500:], notes, added, quota.stats.get('reserved_credits', 0)
