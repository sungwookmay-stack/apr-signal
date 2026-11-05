"""Offline US Medicube RSS configuration and Korean-summary regression tests."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_data as bd
import news_localizer as nl


class USNewsTests(unittest.TestCase):
    def test_three_us_topics_use_free_us_english_rss(self):
        us=[q for q in bd.NEWS_QUERIES if q.get('tag','').startswith('미국 ')]
        self.assertEqual(len(us),3)
        self.assertEqual({q['tag'] for q in us},{
            '미국 오프라인 유통','미국 Amazon·온라인','미국 뷰티기기·신제품'})
        for query in us:
            self.assertEqual(query['country'],'US')
            self.assertEqual(query['gl'],'US')
            self.assertEqual(query['ceid'],'US:en')
            self.assertEqual(query['hl'],'en-US')
            self.assertIn('medicube',query['q'].lower())
        all_topics=[q['tag'] for q in bd.NEWS_QUERIES]
        self.assertIn('칠레 스킨부스터',all_topics)
        self.assertIn('KBTY ETF',all_topics)

    def test_us_articles_get_clear_headline_only_notes(self):
        for topic,term in [('미국 오프라인 유통','입점'),
                           ('미국 Amazon·온라인','Amazon'),
                           ('미국 뷰티기기·신제품','AGE-R')]:
            item={'title':'Medicube expansion in the US - Daily',
                  'category':topic,'country':'US'}
            note=nl.make_topic_note(item,'미국 메디큐브 새 소식')
            self.assertIn(term,note)
            self.assertIn('미국',note)
        self.assertEqual(nl.source_language('US','Medicube at Ulta'),'en')

    def test_rss_us_collection_works_without_paid_apis_and_keeps_translation(self):
        xml=('<?xml version="1.0" encoding="UTF-8"?>'
             '<rss><channel><item>'
             '<title>Medicube expands at US Costco - UPI</title>'
             '<link>https://www.upi.com/example/us-retail</link>'
             '<pubDate>Mon, 19 Oct 2026 13:05:00 GMT</pubDate>'
             '</item></channel></rss>').encode('utf-8')
        topic=next(q for q in bd.NEWS_QUERIES if q['tag']=='미국 오프라인 유통')
        previous={
            'items':[{'title':'Medicube expands at US Costco - UPI',
                      'url':'https://www.upi.com/example/us-retail',
                      'category':'미국 오프라인 유통',
                      'country':'US',
                      'published':'2026-10-19',
                      'title_ko':'메디큐브, 미국 코스트코 매장 확대',
                      'summary_ko':'미국 오프라인 유통 확대 관련 보도입니다.',
                      'summary_basis':'headline_only',
                      'translation_status':'editorial_headline'}]
        }
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'news.json').write_text(json.dumps(previous,ensure_ascii=False),encoding='utf-8')
            calls=[]
            def fake_fetch(url,timeout=12):
                self.assertIn('gl=US',url)
                self.assertIn('ceid=US%3Aen',url)
                calls.append(url)
                return xml
            with patch.object(bd,'DATA',root),\
                 patch.object(bd,'NEWS_QUERIES',[topic]),\
                 patch.object(bd,'fetch',side_effect=fake_fetch),\
                 patch.object(bd,'localize_items',
                   side_effect=lambda rows: (rows,{'headline_only':True})):
                result=bd.collect_news()
        self.assertEqual(len(calls),1)
        self.assertEqual(len(result['items']),1)
        row=result['items'][0]
        self.assertEqual(row['category'],'미국 오프라인 유통')
        self.assertEqual(row['country'],'US')
        self.assertEqual(row['title_ko'],'메디큐브, 미국 코스트코 매장 확대')
        self.assertEqual(row['summary_basis'],'headline_only')
        self.assertEqual(row['published'],'2026-10-19')
        self.assertTrue(row['url'].startswith('https://www.upi.com/'))


if __name__=='__main__':
    unittest.main()
