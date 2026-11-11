import datetime as dt
import unittest
from top100_tracker import extract_page, make_snapshot, track_bestsellers

def item(n,med=False):
    return {'rank':n,'asin':'B'+str(n).zfill(9),
            'title':('medicube PDRN serum' if med else 'Unrelated Brand serum')+' '+str(n),
            'url':'https://www.amazon.com/dp/B'+str(n).zfill(9)}

def payload(start,end,domain='com',category='beauty'):
    return {'category':category,'list':'best_sellers','domain':'amazon.'+domain,
            'items':[item(n,n in (5,42,77)) for n in range(start,end+1)]}

class FakeClient:
    key='test-without-real-key'
    today=dt.date(2026,11,5)
    def __init__(self):
        self.called=[]
    def remaining(self):
        return 750-len(self.called)
    def get(self,route,params,cost):
        self.called.append((route,params['domain'],params['page'],cost))
        a,b=((1,25) if params['page']==1 else (26,50))
        return payload(a,b,params['domain'])

class TrackerTests(unittest.TestCase):
    def test_partial_not_called_exact_top100(self):
        p1=extract_page(payload(1,25),'com')
        p2=extract_page(payload(26,50),'com')
        a=make_snapshot('US',[p1,p2],'2026-11-05')
        self.assertEqual(a['medicube_confirmed_count'],2)
        self.assertEqual(a['coverage_count'],50)
        self.assertFalse(a['coverage_complete'])
        self.assertIsNone(a['new_count'])
    def test_real_complete_only_when_all_100(self):
        a=make_snapshot('US',[extract_page(payload(1,50),'com'),extract_page(payload(51,100),'com')],'2026-11-05')
        self.assertTrue(a['coverage_complete'])
        self.assertEqual(a['coverage_count'],100)
        self.assertEqual(a['medicube_confirmed_count'],3)
    def test_wrong_category_and_domain_rejected(self):
        self.assertIsNone(extract_page(payload(1,25,category='electronics'),'com'))
        self.assertIsNone(extract_page(payload(1,25,domain='de'),'com'))
    def test_duplicates_not_double_counted(self):
        p=extract_page(payload(1,25),'com')
        a=make_snapshot('US',[p,p],'2026-11-05')
        self.assertEqual(a['coverage_count'],25)
        self.assertEqual(a['medicube_confirmed_count'],1)
        self.assertFalse(a['coverage_complete'])
    def test_equal_partial_identity_counts_do_not_prove_entry_or_exit(self):
        cfg={'markets':[{'code':'US','amazon':'amazon.com'}]}
        client=FakeClient()
        old,_,_=track_bestsellers(client,cfg,[])
        old[0]['date']='2026-11-04'
        old[0]['medicube_listings']=[]
        rows,_,_=track_bestsellers(FakeClient(),cfg,old)
        newest=rows[-1]
        self.assertIsNone(newest['new_count'])
        self.assertIsNone(newest['exit_count'])
        self.assertEqual(newest['new_asins'],[])

    def test_country_rotation_bounded_and_idempotent(self):
        client=FakeClient()
        cfg={'markets':[{'code':'US','amazon':'amazon.com'},
                        {'code':'GB','amazon':'amazon.co.uk'},
                        {'code':'DE','amazon':'amazon.de'},
                        {'code':'FR','amazon':'amazon.fr'}]}
        a,stats,n=track_bestsellers(client,cfg,[])
        self.assertEqual(n,3)
        self.assertEqual(len(client.called),6)
        self.assertTrue(all(i['coverage_count']==50 for i in a))
        again,_,n2=track_bestsellers(client,cfg,a)
        self.assertEqual(n2,0)
        self.assertEqual(len(client.called),6)
        self.assertEqual(len(again),len(a))

if __name__=='__main__':unittest.main()
