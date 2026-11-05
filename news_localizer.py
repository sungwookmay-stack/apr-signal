#!/usr/bin/env python3
"""Free-first Korean news digest for the APR SIGNAL static dashboard.

Google News RSS normally contains the headline and a cluster of related links,
NOT the article body. We must NEVER present a headline-derived Korean explainer
as a full-article summary. Curated translations are limited to known headlines;
future headlines use the documented keyless MyMemory translation API when
available. On translation failure, preserve the original and state plainly that
Korean is unavailable. No paid API, browser key, or made-up article body.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
SEEDS = ROOT / 'config/news_korean_seed.json'
USAGE = DATA / 'news_translation_usage.json'
API = 'https://api.mymemory.translated.net/get'
DAILY_CHAR_LIMIT = 4000  # MyMemory anonymous allowance: 5,000 chars/day
MAX_REQUESTS_PER_RUN = 48  # still bounded by 4,000 anonymous chars/day
MAX_QUERY_BYTES = 500
FIELD_KEYS = ('title_ko', 'summary_ko', 'summary_basis',
              'translation_status', 'localized_at')


def read_json(path, fallback):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return fallback


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')


def split_headline(raw):
    """RSS headline usually ends with ' - Publisher'. Keep publisher separate."""
    title = html.unescape(re.sub(r'\s+', ' ', str(raw or '')).strip())
    if ' - ' not in title:
        return title[:250], ''
    headline, publisher = title.rsplit(' - ', 1)
    if len(publisher) > 95 or not headline:
        return title[:250], ''
    return headline.strip()[:250], publisher.strip()[:95]


def source_language(country, headline):
    if re.search(r'[가-힣]', headline):
        return 'ko'
    return {'BR': 'pt', 'AR': 'es', 'CL': 'es', 'JP': 'ja', 'KR': 'ko'}.get(country, 'en')


def make_topic_note(item, title_ko):
    """Editorial context from headline/category; not an article-body summary."""
    category = str(item.get('category') or '')
    raw = split_headline(item.get('title'))[0].lower()
    # US-market reporting is a topic tag, not a guarantee of a US publisher.
    # RSS headlines only: do not claim specific sales/store counts without source review.
    if '미국 오프라인' in category:
        return ('미국의 메디큐브 입점·오프라인 유통 채널 확대 관련 보도입니다. '
                '매장 입점 사실과 실제 매장별 판매량·재주문은 구분해서 확인해야 합니다.')
    if '미국 Amazon' in category:
        return ('미국 Amazon·TikTok Shop 등 온라인 채널에서 메디큐브 판매·검색 동향을 다룬 기사입니다. '
                '행사 매출이나 순위와 분기 전체 매출액은 직접 같지 않습니다.')
    if '미국 뷰티기기' in category:
        return ('미국 시장의 메디큐브 AGE-R 뷰티기기 또는 스킨케어 신제품 관련 보도입니다. '
                '기사 제목만으로 판매량·제품 인증·매출 기여도를 확정할 수 없습니다.')
    if '브라질' in category:
        return ('브라질 현지의 메디큐브 제품과 K-뷰티 유통 동향을 다룬 보도입니다. '
                '실제 판매량·공식 유통 계약 여부는 별도 확인이 필요합니다.')
    if '아르헨티나' in category:
        return ('아르헨티나 현지의 메디큐브·스킨케어 유통 관련 보도입니다. '
                '검색 관심도와 실제 매출·수입실적은 구분해서 확인해야 합니다.')
    if 'KBTY' in category:
        return ('K-뷰티 ETF의 등록·상장 동향을 다룬 보도입니다. '
                '실제 상장 여부와 에이피알 편입 비중은 운용사·거래소 발표로 확인해야 합니다.')
    if 'HIFU' in category or 'RF' in category:
        return ('에이피알의 의료미용기기 사업 확대와 관련한 기사입니다. '
                '제품 인허가·출시·실제 매출 발생 여부는 별도 검증이 필요합니다.')
    if '칠레 클리닉' in category:
        return ('칠레 현지 미용 시술과 클리닉 시장 관련 기사입니다. '
                '메디큐브 제품의 실제 도입·재주문 여부는 확인되지 않았습니다.')
    if '칠레' in category:
        if 'medicube' in raw or '메디큐브' in raw:
            return ('칠레 현지 매체가 메디큐브의 스킨부스터 또는 주사형 미용 제품을 다뤘습니다. '
                    '기사 제목만으로 판매량·품목허가·재주문 여부를 판단할 수는 없습니다.')
        return ('칠레 현지의 피부미용·스킨부스터 관련 보도입니다. '
                '에이피알 제품의 실제 판매 실적과는 구분해서 살펴봐야 합니다.')
    if '중동' in category:
        return ('중동 시장의 뷰티·스킨부스터 사업과 관련한 기사입니다. '
                '현지 입점·출고·판매 실적은 공식 근거로 확인해야 합니다.')
    return ('기사 제목에 나타난 현지 시장 동향을 소개합니다. '
            '실제 실적이나 인허가를 입증하는 자료는 별도로 확인해야 합니다.')


def valid_translation(original, translated):
    result = html.unescape(str(translated or '')).strip()
    if (not result or len(result) > 600 or
        'MYMEMORY WARNING' in result.upper() or
        'PLEASE SELECT TWO DISTINCT' in result.upper() or
        result.casefold() == original.casefold()):
        return None
    # An English/Spanish title left in Latin characters is not Korean.
    if not re.search(r'[가-힣]', result):
        return None
    return result


class FreeTranslator:
    def __init__(self, utc_day=None, transport=None, utc_now=None):
        self.now = utc_now or dt.datetime.now(dt.timezone.utc)
        if self.now.tzinfo is None:
            raise ValueError('UTC-aware timestamp required')
        self.day = utc_day or self.now.date().isoformat()
        previous = read_json(USAGE, {})
        if not isinstance(previous, dict):
            previous = {}
        rolling = previous.get('events')
        if not isinstance(rolling, list):
            rolling = []
            # Migrate an older usage file which recorded only daily totals.
            # For safety, count recent un-timestamped calls conservatively.
            try:
                old_date = dt.date.fromisoformat(previous.get('day', ''))
                old_chars = int(previous.get('reserved_chars') or 0)
                if (0 <= (self.now.date() - old_date).days <= 1 and old_chars > 0):
                    rolling = [{'at_utc': self.now.isoformat(timespec='seconds'),
                                'chars': min(old_chars, DAILY_CHAR_LIMIT)}]
            except (ValueError, TypeError):
                pass
        cutoff = self.now - dt.timedelta(hours=24)
        events = []
        for event in rolling:
            if not isinstance(event, dict):
                continue
            try:
                when = dt.datetime.fromisoformat(event['at_utc'])
                chars = int(event['chars'])
                if when.tzinfo and cutoff <= when <= self.now and chars > 0:
                    events.append({'at_utc': when.isoformat(timespec='seconds'),
                                   'chars': min(chars, DAILY_CHAR_LIMIT)})
            except (KeyError, TypeError, ValueError):
                continue
        if previous.get('day') != self.day:
            previous = {'day': self.day, 'reserved_chars': 0, 'calls': 0}
        self.usage = previous
        self.usage['events'] = events
        self.transport = transport or self._http_get
        self.errors = []
        self.skipped_quota = 0

    @staticmethod
    def _http_get(url):
        request = urllib.request.Request(
            url, headers={'Accept': 'application/json',
                          'User-Agent': 'APR-SIGNAL-FreeNews/1.0'})
        with urllib.request.urlopen(request, timeout=8) as response:
            return json.loads(response.read(30000).decode('utf-8'))

    def translate(self, title, language):
        if not title or language == 'ko':
            return title if language == 'ko' else None
        char_count = len(title)
        rolling_chars = sum(e['chars'] for e in self.usage['events'])
        if (len(title.encode('utf-8')) > MAX_QUERY_BYTES or
            self.usage.get('reserved_chars', 0) + char_count > DAILY_CHAR_LIMIT or
            rolling_chars + char_count > DAILY_CHAR_LIMIT or
            self.usage.get('calls', 0) >= MAX_REQUESTS_PER_RUN):
            self.skipped_quota += 1
            return None

        # Both UTC-day and rolling 24h limits protect the morning/afternoon
        # KST schedule across the UTC date boundary. Reserve before network.
        self.usage['reserved_chars'] += char_count
        self.usage['calls'] += 1
        self.usage['events'].append({
            'at_utc': self.now.isoformat(timespec='seconds'),
            'chars': char_count
        })
        write_json(USAGE, self.usage)
        query = urllib.parse.urlencode({'q': title, 'langpair': language + '|ko'})
        try:
            doc = self.transport(API + '?' + query)
            if not isinstance(doc, dict) or int(doc.get('responseStatus', 0)) != 200:
                self.errors.append('번역 응답 오류')
                return None
            return valid_translation(title, (doc.get('responseData') or {}).get('translatedText'))
        except (urllib.error.URLError, TimeoutError, ValueError, TypeError, OSError):
            self.errors.append('무료 번역 서비스 접근 불가')
            return None


def localize_items(items, translator=None):
    """Localize existing snapshots; preserve cached successful translations."""
    translator = translator or FreeTranslator()
    seeds = read_json(SEEDS, {})
    updated = []
    translated_count, seeded_count, unavailable_count = 0, 0, 0
    for raw in items:
        item = dict(raw)
        headline, source = split_headline(item.get('title'))
        item['publisher'] = source
        if not headline:
            updated.append(item)
            continue
        seed = seeds.get(headline)
        if isinstance(seed, dict) and seed.get('title_ko') and seed.get('summary_ko'):
            item.update({
                'title_ko': str(seed['title_ko']).strip()[:250],
                'summary_ko': str(seed['summary_ko']).strip()[:380],
                'summary_basis': 'headline_only',
                'translation_status': 'editorial_headline',
                'localized_at': translator.day
            })
            seeded_count += 1
        elif item.get('title_ko') and item.get('summary_basis') == 'headline_only':
            # Already localized for this exact headline in an earlier run.
            item['summary_ko'] = item.get('summary_ko') or make_topic_note(item, item['title_ko'])
        else:
            lang = source_language(item.get('country'), headline)
            ko = headline if lang == 'ko' else translator.translate(headline, lang)
            if ko:
                item.update({
                    'title_ko': ko[:250],
                    'summary_ko': make_topic_note(item, ko),
                    'summary_basis': 'headline_only',
                    'translation_status': 'original_korean' if lang == 'ko' else 'machine_headline',
                    'localized_at': translator.day
                })
                translated_count += 1
            else:
                for key in FIELD_KEYS:
                    item.pop(key, None)
                item['translation_status'] = 'pending'
                unavailable_count += 1
        updated.append(item)

    stats = {
        'method': 'curated headline + free machine translation; article body not accessed',
        'headline_only': True,
        'localized': seeded_count + translated_count,
        'editorial': seeded_count,
        'new_or_native': translated_count,
        'pending': unavailable_count,
        'free_translation_chars_reserved_today': translator.usage.get('reserved_chars', 0),
        'free_translation_chars_daily_cap': DAILY_CHAR_LIMIT,
        'free_translation_chars_reserved_24h': sum(e['chars'] for e in translator.usage.get('events', [])),
        'skipped_quota': translator.skipped_quota,
        'errors': translator.errors[:5]
    }
    return updated, stats


def localize_saved_news(path=None):
    path = Path(path or DATA / 'news.json')
    data = read_json(path, {})
    if not isinstance(data, dict) or not isinstance(data.get('items'), list):
        raise ValueError('뉴스 저장 파일이 없습니다.')
    data['items'], data['korean_digest'] = localize_items(data['items'])
    data['source_note'] = ('Google News RSS 제목과 원문 링크를 한국어로 정리. '
                           '본문 전문은 수집하지 않으며 요약은 제목 기반으로 표시.')
    data['korean_updated_at'] = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    write_json(path, data)
    return data['korean_digest']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Free Korean RSS headline digest')
    parser.add_argument('--refresh-file', action='store_true')
    args = parser.parse_args()
    if args.refresh_file:
        print(json.dumps(localize_saved_news(), ensure_ascii=False))
