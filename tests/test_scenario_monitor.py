import copy
import json
import tempfile
import unittest
from pathlib import Path
import scenario_monitor as sm


class ScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.data=Path(self.temp.name)
        self.now='2027-07-12T01:00:00+00:00'

    def tearDown(self):
        self.temp.cleanup()

    def save(self,name,value):
        (self.data/(name+'.json')).write_text(json.dumps(value))

    def evidence(self,sid='bull'):
        cfg=sm.read(sm.ROOT/'config/scenario_criteria.json',{})
        return [dict(condition_id=c['id'],review_status='verified',evidence_type='direct',covers_entire_condition=True,
            stance='supported',source_url='https://apr-in.com/ir/example',quote='Test fixture only',reason='Test only',
            known_at='2027-07-02',published_at='2027-07-01',observed_at='2027-07-02',period_end='2027-06-30')
            for s in cfg['scenarios'] if s['id']==sid for c in s['conditions']]

    def test_all_twelve_exact_no_numeric_thresholds(self):
        x=sm.evaluate(self.data,self.now)
        self.assertEqual([len(s['conditions']) for s in x['scenarios']],[4,4,4])
        self.assertEqual(x['classification'],'pending')
        self.assertEqual(len(x['missing']),12)

    def test_complete_direct_evidence_classifies(self):
        self.save('scenario_evidence',{'evidence':self.evidence()})
        self.assertEqual(sm.evaluate(self.data,self.now)['classification'],'bull')

    def test_partial_not_enough(self):
        self.save('scenario_evidence',{'evidence':self.evidence()[:3]})
        self.assertEqual(sm.evaluate(self.data,self.now)['classification'],'pending')

    def test_future_unknown_proxy_unreviewed_rejected(self):
        for key,value in [('known_at','2028-01-01'),('published_at','2028-01-01'),('observed_at',None),('period_end','2028-01-01'),
                          ('evidence_type','proxy'),('review_status','unreviewed'),('source_url','https://news.example.com'),
                          ('covers_entire_condition',False),('quote','')]:
            with self.subTest(key=key):
                rows=self.evidence(); rows[0][key]=value
                self.save('scenario_evidence',{'evidence':rows})
                self.assertEqual(sm.evaluate(self.data,self.now)['classification'],'pending')

    def test_conflict_pending(self):
        rows=self.evidence(); conflict=copy.deepcopy(rows[0]); conflict['stance']='contradicted';rows.append(conflict)
        self.save('scenario_evidence',{'evidence':rows})
        out=sm.evaluate(self.data,self.now)
        self.assertEqual(out['classification'],'pending')
        self.assertEqual(out['scenarios'][2]['conditions'][0]['status'],'conflicting')

    def test_two_matches_pending(self):
        self.save('scenario_evidence',{'evidence':self.evidence()+self.evidence('base')})
        self.assertEqual(sm.evaluate(self.data,self.now)['classification'],'pending')

    def test_daily_idempotence_and_revision(self):
        sm.update(self.data,self.now)
        out=sm.update(self.data,'2027-07-12T02:00:00+00:00')
        self.assertEqual(len(out['history']),1)
        self.assertEqual(len(out['latest']['revisions']),0)
        self.save('scenario_evidence',{'evidence':self.evidence()})
        out=sm.update(self.data,'2027-07-12T03:00:00+00:00')
        self.assertEqual(len(out['history']),1)
        self.assertEqual(out['latest']['revisions'][0]['classification'],'pending')
        out=sm.update(self.data,'2027-07-13T01:00:00+00:00')
        self.assertEqual(len(out['history']),2)

    def test_no_backfill_or_reverse_time(self):
        sm.update(self.data,self.now)
        for date in ['2026-11-01T00:00:00+00:00','2026-11-12T00:00:00+00:00']:
            with self.assertRaises(ValueError):sm.update(self.data,date)

    def test_kst_day(self):
        self.assertEqual(sm.evaluate(self.data,'2026-11-11T16:00:00+00:00')['date'],'2026-11-12')

    def test_date_only_end_of_day_conservative(self):
        self.assertFalse(sm.date_known('2026-11-12',sm.moment('2026-11-12T01:00:00+00:00')))
        self.assertTrue(sm.date_known('2026-11-11',sm.moment(self.now)))

    def test_financial_context_excludes_future_and_third_party(self):
        rows=[dict(accounting_basis='IFRS18',period='2026Q1',asof='2026-03-31',available_from='2026-05-15',sales=100,op=20,source='test',source_url='https://apr-in.com/a'),
              dict(period='2026Q2',asof='2026-06-30',available_from='2028-01-01',sales=100,op=20,source_url='https://apr-in.com/b'),
              dict(period='2026Q3',asof='2026-09-30',available_from='2026-10-01',sales=100,op=20,source_url='https://dartbrief.com/a')]
        self.save('financials',{'quarterly':rows})
        context=sm.evaluate(self.data,self.now)['context']
        self.assertEqual(next(c for c in context if c['id']=='2026Q1_margin')['value'],20)
        self.assertFalse(any(c['id'] in ('2026Q2_sales','2026Q3_sales') for c in context))
        self.assertEqual(next(c for c in context if c['id']=='ytd_sales')['value'],100)

    def test_missing_quarter_not_ytd(self):
        self.save('financials',{'quarterly':[dict(period='2026Q2',asof='2026-06-30',available_from='2026-08-14',sales=100,op=20,source_url='https://apr-in.com/a')]})
        self.assertFalse(any(c['id']=='ytd_sales' for c in sm.evaluate(self.data,self.now)['context']))

    def test_nan_not_serialized(self):
        self.save('financials',{'quarterly':[dict(accounting_basis='IFRS18',period='2026Q1',asof='2026-03-31',available_from='2026-05-15',sales=float('nan'),op=20,source_url='https://apr-in.com/a')]})
        self.assertFalse(any(c['id']=='2026Q1_sales' for c in sm.evaluate(self.data,self.now)['context']))

    def test_future_hypothesis_cannot_be_confirmed_early(self):
        rows=self.evidence()
        for row in rows:
            row.update(known_at='2026-11-01',observed_at='2026-11-01',published_at='2026-11-01',period_end='2026-10-31')
        self.save('scenario_evidence',{'evidence':rows})
        self.assertEqual(sm.evaluate(self.data,'2026-11-12T00:00:00+00:00')['classification'],'pending')

    def test_supplement_known_at_and_partial_not_full(self):
        before=sm.evaluate(self.data,'2026-11-01T00:00:00+00:00')
        self.assertFalse(any(c['id']=='costco' for c in before['context']))
        after=sm.evaluate(self.data,'2026-11-12T00:00:00+00:00')
        self.assertEqual(after['classification'],'pending')
        self.assertEqual(after['provisional']['status'],'reference_signal')
        bull=next(c for c in after['provisional']['counts'] if c['id']=='bull')
        self.assertEqual(bull['partial_support'],2)
        self.assertEqual(bull['confirmed'],0)

    def test_stale_facts_visible_but_not_scored(self):
        out=sm.evaluate(self.data,'2027-03-01T00:00:00+00:00')
        self.assertEqual(out['provisional']['status'],'pending')
        fact=next(c for c in out['context'] if c['id']=='costco')
        self.assertFalse(fact['signal_eligible'])
        self.assertIn('120',fact['signal_exclusion_reason'])

    def test_new_quarter_supersedes_old_signal(self):
        self.save('financials',{'quarterly':[dict(period='2026Q4',asof='2026-12-31',available_from='2027-01-02',sales=100,op=20,source_url='https://apr-in.com/new')]})
        out=sm.evaluate(self.data,'2027-01-04T00:00:00+00:00')
        fact=next(c for c in out['context'] if c['id']=='ir26q3_europe_mix')
        self.assertFalse(fact['signal_eligible'])
        self.assertIn('최신 분기',fact['signal_exclusion_reason'])
        self.assertEqual(out['provisional']['status'],'pending')

    def test_conflicting_direct_evidence_blocks_provisional(self):
        rows=self.evidence()[:1]
        rows[0].update(known_at='2027-01-02',observed_at='2027-01-02',published_at='2027-01-02',period_end='2026-12-31')
        other=copy.deepcopy(rows[0]);other['stance']='contradicted';rows.append(other)
        self.save('scenario_evidence',{'evidence':rows})
        out=sm.evaluate(self.data,'2027-01-04T00:00:00+00:00')
        self.assertEqual(out['provisional']['status'],'pending')
        self.assertEqual(next(c for c in out['provisional']['counts'] if c['id']=='bull')['conflicting'],1)

    def test_accounting_basis_required_for_sum(self):
        self.save('financials',{'quarterly':[dict(period='2026Q1',asof='2026-03-31',available_from='2026-05-15',sales=100,op=20,source_url='https://apr-in.com/a')]})
        self.assertFalse(any(c['id']=='ytd_sales' for c in sm.evaluate(self.data,self.now)['context']))

    def test_receipt_links_supplement_official_source(self):
        self.save('financials',{'quarterly':[dict(accounting_basis='IFRS18',period='2026Q1',asof='2026-03-31',available_from='2026-05-15',sales=100,op=20)]})
        self.save('dart_financials',{'filings':[dict(period='2026Q1',receipt_numbers=['20260515000123'])]})
        self.assertIn('20260515000123',next(c['source_url'] for c in sm.evaluate(self.data,self.now)['context'] if c['id']=='2026Q1_sales'))


if __name__=='__main__':
    unittest.main()
