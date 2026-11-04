import datetime as dt
import unittest

from scrapedo_bestsellers import normalize_page,track_scrapedo
from top100_tracker import make_snapshot

def asin(n):
    return 'B'+str(n).zfill(9)

def payload(page):
    start=1 if page==1 else 51
    return {'category':'beauty','type':'bestsellers','page':page,
        'ranking':[{'rank':i,'asin':asin(i),'url':'https://www.amazon.co.uk/dp/'+asin(i)}
                   for i in range(start,start+50)],
        'products':[{'rank':i,'asin':asin(i),
            'title':('medicube PDRN serum ' if i in (2,21,65,77) else 'ordinary beauty product ')+str(i)}
            for i in range(start,start+30)]}

class FakeQuota:
    day=dt.date(2026,11,6)
    token='mock'
    errors=[]
    stats={'reserved_credits':18}
    def __init__(self):self.calls=[]
    def can_call(self):return True
    def get(self,code,page):
        self.calls.append((code,page))
        return payload(page)

class ScrapeTests(unittest.TestCase):
    def test_ranking_100_with_only_60_titles_is_not_exact_brand_count(self):
        p1=normalize_page(payload(1),1)
        p2=normalize_page(payload(2),2)
        self.assertEqual(len(p1),50)
        self.assertEqual(len(p2),50)
        snap=make_snapshot('GB',[p1,p2],'2026-11-06')
        self.assertEqual(snap['coverage_count'],100)
        self.assertTrue(snap['rank_coverage_complete'])
        self.assertFalse(snap['coverage_complete'])
        self.assertEqual(snap['identity_coverage_count'],60)
        self.assertEqual(snap['unidentified_count'],40)
        self.assertEqual(snap['medicube_confirmed_count'],4)
    def test_known_verified_asin_can_fill_rank_only_slot(self):
        known={asin(45):'medicube official PDRN pad'}
        page=normalize_page(payload(1),1,known)
        self.assertEqual(page[44][2],'medicube official PDRN pad')
    def test_wrong_category_and_page_rejected(self):
        p=payload(1);p['category']='home'
        self.assertIsNone(normalize_page(p,1))
        self.assertIsNone(normalize_page(payload(1),2))
    def test_uk_and_us_daily_plus_one_rotation(self):
        fake=FakeQuota()
        cfg={'markets':[{'code':c,'amazon':'amazon.'+dom} for c,dom in
             [('US','com'),('GB','co.uk'),('DE','de'),('FR','fr')]]}
        rows,status,n,credits=track_scrapedo('test',cfg,[],client=fake)
        self.assertEqual(n,3)
        self.assertEqual(len(fake.calls),6)
        self.assertIn('US',{x['country'] for x in rows})
        self.assertIn('GB',{x['country'] for x in rows})
        self.assertTrue(all(x['coverage_count']==100 for x in rows))
        self.assertTrue(all(not x['coverage_complete'] for x in rows))
        rows2,notes,n2,_=track_scrapedo('test',cfg,rows,client=fake)
        self.assertEqual(n2,0)
        self.assertEqual(len(fake.calls),6)

if __name__=='__main__':unittest.main()
