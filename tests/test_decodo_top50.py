import copy
import datetime as dt
import unittest
import urllib.error
from decodo_top50 import collect, eligibility, inspect_top50, display_snapshot, candidate_brands, MARKETS

NOW=dt.datetime(2026,11,8,22,30,tzinfo=dt.timezone.utc) # Monday KST
CRON='30 22 * * *'
ENV={'DECODO_TOP50_ENABLED':'true','DECODO_PUBLIC_USE_AUTHORIZED':'true',
     'DECODO_FREE_PLAN_CONFIRMED':'true','GITHUB_EVENT_NAME':'schedule',
     'GITHUB_EVENT_SCHEDULE':CRON,'GITHUB_RUN_ATTEMPT':'1','DECODO_API_KEY':'test-not-a-real-key'}
def page(domain='com'):
    return {'url':f'https://www.amazon.{domain}/gp/bestsellers/beauty', 'page':1,
            'results':[{'pos':i,'asin':f'B{i:09d}','title':f'Product {i}'} for i in range(1,51)]}

class Tests(unittest.TestCase):
    def test_schedule_and_utc_boundary(self):
        self.assertIsNone(eligibility(ENV,NOW,CRON))
        self.assertEqual(eligibility(ENV,NOW+dt.timedelta(days=1),CRON),'excluded_kst_day')
        self.assertEqual(eligibility(ENV,NOW+dt.timedelta(days=3),CRON),'excluded_kst_day')
        for days in (2,4,5,6): self.assertIsNone(eligibility(ENV,NOW+dt.timedelta(days=days),CRON))
        self.assertEqual(eligibility(ENV,NOW-dt.timedelta(minutes=1),CRON),'outside_morning_window')
        self.assertEqual(eligibility(ENV,NOW+dt.timedelta(hours=5),CRON),'outside_morning_window')
        self.assertEqual(eligibility(ENV,NOW,'0 22 * * *'),'morning_time_unconfigured')
    def test_no_unintended_network(self):
        for key,value in [('GITHUB_EVENT_NAME','workflow_dispatch'),('GITHUB_EVENT_NAME','push'),
                          ('GITHUB_EVENT_SCHEDULE','0 7 * * *'),('GITHUB_RUN_ATTEMPT','2'),
                          ('DECODO_TOP50_ENABLED','false'),('DECODO_PUBLIC_USE_AUTHORIZED','false'),
                          ('DECODO_FREE_PLAN_CONFIRMED','false'),('DECODO_API_KEY','')]:
            env={**ENV,key:value}
            def forbidden(*a): self.fail('unexpected request')
            self.assertEqual(collect({},env,NOW,CRON,lambda s:None,forbidden)['attempts'],0)
    def test_exact_identity(self):
        good=page()
        self.assertEqual(len(inspect_top50({'results':[{'content':good}]},'US',NOW)['items']),50)
        for mutation in ('short','duplicate','rank','title','market','page'):
            bad=copy.deepcopy(good)
            if mutation=='short': bad['results'].pop()
            if mutation=='duplicate': bad['results'][1]['asin']=bad['results'][0]['asin']
            if mutation=='rank': bad['results'][49]['pos']=100
            if mutation=='title': bad['results'][0]['title']=''
            if mutation=='market': bad['url']='https://www.amazon.co.uk/gp/bestsellers/beauty'
            if mutation=='page': bad['page']=2
            with self.assertRaises(ValueError): inspect_top50(bad,'US',NOW)
    def test_once_and_reserve_before_request(self):
        state={}; persisted=[]
        def save(s): persisted.append(copy.deepcopy(s))
        def request(key,domain):
            self.assertTrue(persisted)
            self.assertGreater(persisted[-1]['attempts_by_month']['2026-11'],0)
            return page(domain)
        self.assertEqual(collect(state,ENV,NOW,CRON,save,request)['attempts'],12)
        self.assertEqual(collect(state,ENV,NOW,CRON,save,request)['attempts'],0)
        self.assertEqual(len(state['latest_complete']),12)
    def test_partial_retains_cache_and_cap(self):
        state={'latest_complete':{'US':{'old':True}},'attempts_by_month':{'2026-11':299}}
        def bad(*a): raise ValueError('bad response')
        result=collect(state,ENV,NOW,CRON,lambda s:None,bad)
        self.assertEqual(result['reason'],'local_monthly_attempt_cap')
        self.assertEqual(result['attempts'],1)
        self.assertEqual(state['latest_complete']['US'],{'old':True})
        self.assertEqual(state['latest_checks']['US']['diagnostic_code'],'invalid_response')
    def test_http_failure_pauses_without_body(self):
        def bad(*a): raise urllib.error.HTTPError('redacted',429,'SECRET',{},None)
        result=collect({},ENV,NOW,CRON,lambda s:None,bad)
        self.assertEqual(result,{'status':'paused','reason':'provider_http_error','attempts':1})
    def test_movement_candidates_and_exits(self):
        old=inspect_top50(page(),'US',NOW)
        old['items'][0]['title']='medicube cream'
        new=copy.deepcopy(old)
        new['observed_at_utc']=(NOW+dt.timedelta(days=2)).isoformat()
        new['items'][0]['rank']=5
        result=display_snapshot(new,old)
        self.assertEqual(result['candidate_count'],1)
        self.assertEqual(result['verified_count'],0)
        self.assertEqual(result['items'][0]['rank_change'],-4)
        self.assertEqual(display_snapshot(new)['items'][0]['movement'],'first_observation')
        self.assertEqual(display_snapshot(new,old,{'B000000001'})['verified_count'],1)
        new['items'][0]['asin']='B999999999'
        result=display_snapshot(new,old)
        self.assertEqual(result['items'][0]['movement'],'entered_top50')
        self.assertEqual(result['exited'][0]['movement'],'not_in_current_top50')
        self.assertIsNone(result['exited'][0]['current_rank'])
    def test_explicit_initial_run_once_and_expiry(self):
        env={**ENV,'GITHUB_EVENT_NAME':'push','DECODO_INITIAL_RUN':'initial-20261112'}
        when=dt.datetime(2026,11,11,16,0,tzinfo=dt.timezone.utc)
        self.assertIsNone(eligibility(env,when,CRON))
        self.assertEqual(eligibility(env,when+dt.timedelta(days=1),CRON),'initial_run_expired')
        self.assertEqual(eligibility({**env,'GITHUB_RUN_ATTEMPT':'2'},when,CRON),'rerun_blocked')
        state={}
        result=collect(state,env,when,CRON,lambda s:None,lambda key,domain:page(domain))
        self.assertEqual(result['attempts'],12)
        def forbidden(*a): self.fail('initial run duplicated')
        result=collect(state,env,when,CRON,lambda s:None,forbidden)
        self.assertEqual(result['reason'],'initial_run_already_consumed')
    def test_uae_recheck_is_exactly_once_and_one_market(self):
        env={**ENV,'GITHUB_EVENT_NAME':'push','DECODO_INITIAL_RUN':'uae-recheck-20261112'}
        when=dt.datetime(2026,11,11,16,0,tzinfo=dt.timezone.utc)
        state={'attempts_by_month':{'2026-11':12},'attempts_by_day':{'2026-11-12':list(MARKETS)}}
        calls=[]
        def req(key,domain):calls.append(domain);return page(domain)
        self.assertEqual(collect(state,env,when,CRON,lambda s:None,req)['attempts'],1)
        self.assertEqual(calls,['ae'])
        self.assertEqual(state['attempts_by_month']['2026-11'],13)
        self.assertEqual(collect(state,env,when,CRON,lambda s:None,req)['attempts'],0)
        self.assertEqual(calls,['ae'])
    def test_other_brands_and_ambiguity(self):
        self.assertEqual(candidate_brands('APRIL SKIN cleansing balm'),['aprilskin'])
        self.assertEqual(candidate_brands('FORMENT perfume'),['forment'])
        self.assertEqual(candidate_brands('GLAM.D Bio'),['glamd'])
        self.assertEqual(candidate_brands('nerdy skin NDY cream'),[])
        self.assertEqual(candidate_brands('notmedicube'),[])
        now=inspect_top50(page(),'US',NOW)
        now['items'][0]['title']='APRILSKIN cleansing balm'
        now['items'][1]['title']='medicube APRILSKIN comparison kit'
        result=display_snapshot(now)
        self.assertEqual(result['brands']['aprilskin']['candidate_count'],1)
        self.assertEqual(result['brands']['medicube']['candidate_count'],0)
        self.assertEqual(len(result['ambiguous_items']),1)
    def test_failed_reservation_prevents_request(self):
        def save(s): raise OSError('disk full')
        def forbidden(*a): self.fail('unexpected request')
        with self.assertRaises(OSError): collect({},ENV,NOW,CRON,save,forbidden)

if __name__=='__main__': unittest.main()
