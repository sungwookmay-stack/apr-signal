import tempfile
import unittest
import urllib.error
import urllib.parse
from pathlib import Path
from unittest.mock import patch

import news_localizer as nl


class KoreanNewsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(nl, 'USAGE', Path(self.tmp.name) / 'translation_usage.json')
        p.start()
        self.addCleanup(p.stop)

    def test_seeded_chile_news_is_readable_korean(self):
        raw = ('Medicube lanza en Chile PN Skin Booster: qué es y cómo funciona '
               'el nuevo inyectable coreano - DUPLOS.CL')
        item = {'title': raw, 'country': 'CL', 'category': '칠레 스킨부스터',
                'url': 'https://news.google.com/rss/articles/test'}
        messages, status = nl.localize_items([item], nl.FreeTranslator(
            utc_day='2026-11-05', transport=lambda _: self.fail('unexpected translation')))
        self.assertIn('PN 스킨부스터', messages[0]['title_ko'])
        self.assertIn('칠레', messages[0]['summary_ko'])
        self.assertEqual(messages[0]['summary_basis'], 'headline_only')
        self.assertEqual(messages[0]['translation_status'], 'editorial_headline')
        self.assertEqual(messages[0]['url'], item['url'])
        self.assertEqual(messages[0]['publisher'], 'DUPLOS.CL')
        self.assertTrue(status['headline_only'])

    def test_unseen_english_headline_uses_free_translation_and_caches(self):
        called = []
        def fake(url):
            called.append(urllib.parse.parse_qs(urllib.parse.urlparse(url).query))
            return {'responseStatus': 200,
                    'responseData': {'translatedText': '메디큐브가 새 판매 채널을 발표했다'}}
        item = {'title': 'Medicube announces a new retail channel - Local Press',
                'country': 'US', 'category': 'KBTY ETF', 'url': 'https://example.org/a'}
        translator = nl.FreeTranslator(utc_day='2026-11-05', transport=fake)
        first, stats = nl.localize_items([item], translator)
        self.assertEqual(first[0]['title_ko'], '메디큐브가 새 판매 채널을 발표했다')
        self.assertEqual(first[0]['summary_basis'], 'headline_only')
        self.assertIn('ETF', first[0]['summary_ko'])
        self.assertEqual(called[0]['langpair'], ['en|ko'])
        self.assertEqual(len(called), 1)
        second, _ = nl.localize_items(first, translator)
        self.assertEqual(second[0]['title_ko'], first[0]['title_ko'])
        self.assertEqual(len(called), 1, 'Already localized headline must not be repurchased')

    def test_spanish_language_and_original_title_are_preserved(self):
        called = []
        def fake(url):
            called.append(urllib.parse.parse_qs(urllib.parse.urlparse(url).query))
            return {'responseStatus': 200,
                    'responseData': {'translatedText': '칠레에서 새로운 현지 사업 확대'}}
        raw = 'Empresa de belleza anuncia una expansión en Chile - Diario'
        rows, _ = nl.localize_items([
            {'title': raw, 'country': 'CL', 'category': '칠레 스킨부스터'}
        ], nl.FreeTranslator(utc_day='2026-11-05', transport=fake))
        self.assertEqual(rows[0]['title'], raw)
        self.assertEqual(called[0]['langpair'], ['es|ko'])
        self.assertEqual(rows[0]['publisher'], 'Diario')
        self.assertEqual(rows[0]['translation_status'], 'machine_headline')

    def test_translation_failure_shows_pending_not_fabricated_summary(self):
        def fail(_):
            raise urllib.error.URLError('blocked')
        rows, stats = nl.localize_items([
            {'title': 'A new beauty business arrived in Chile - Daily',
             'country': 'CL', 'category': '칠레 스킨부스터'}
        ], nl.FreeTranslator(utc_day='2026-11-05', transport=fail))
        self.assertNotIn('title_ko', rows[0])
        self.assertNotIn('summary_ko', rows[0])
        self.assertEqual(rows[0]['translation_status'], 'pending')
        self.assertEqual(stats['pending'], 1)

    def test_free_char_budget_is_reserved_before_call(self):
        def fake(_):
            return {'responseStatus': 200,
                    'responseData': {'translatedText': '한국어 번역 완료'}}
        tr = nl.FreeTranslator(utc_day='2026-11-05', transport=fake)
        tr.usage['reserved_chars'] = nl.DAILY_CHAR_LIMIT - 8
        self.assertIsNone(tr.translate('A headline requiring more chars', 'en'))
        self.assertEqual(tr.usage['calls'], 0)
        self.assertEqual(tr.skipped_quota, 1)
        self.assertEqual(tr.usage['reserved_chars'], nl.DAILY_CHAR_LIMIT - 8)

    def test_brazil_and_argentina_news_languages(self):
        self.assertEqual(nl.source_language('BR','Medicube no Brasil'),'pt')
        self.assertEqual(nl.source_language('AR','Medicube en Argentina'),'es')
        self.assertIn('매출',nl.make_topic_note(
            {'category':'아르헨티나 메디큐브'},'메디큐브 뉴스'))
    def test_native_korean_remains_korean_without_external_call(self):
        item = {'title': '에이피알 의료기기 사업 확대 - 한국경제',
                'country': 'KR', 'category': '의료기기 HIFU·RF'}
        rows, stats = nl.localize_items([item], nl.FreeTranslator(
            utc_day='2026-11-05', transport=lambda _: self.fail('no call')))
        self.assertIn('에이피알 의료기기', rows[0]['title_ko'])
        self.assertEqual(rows[0]['translation_status'], 'original_korean')
        self.assertEqual(stats['free_translation_chars_reserved_today'], 0)

    def test_non_korean_machine_output_is_rejected(self):
        self.assertIsNone(nl.valid_translation('Hello world', 'Hello world'))
        self.assertIsNone(nl.valid_translation('Hello world', 'Something in English'))
        self.assertEqual(nl.valid_translation('Hola', '안녕하세요'), '안녕하세요')

    def test_html_entities_decoded_for_publisher_split(self):
        title, publisher = nl.split_headline('APR &amp; K-beauty launches - News Source')
        self.assertEqual(title, 'APR & K-beauty launches')
        self.assertEqual(publisher, 'News Source')


if __name__ == '__main__':
    unittest.main()
