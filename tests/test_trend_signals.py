import datetime as dt
import unittest
import trend_signals as ts

DAY=dt.date(2026,11,8)

def weekly(country,term,values,dataset='US_TRENDS_1',end=dt.date(2026,11,4)):
    start=end-dt.timedelta(days=7*(len(values)-1))
    return [{'country':country,'term':term,
             'date':(start+dt.timedelta(days=7*i)).isoformat(),
             'index':n,'source':'API.SH Google Trends','dataset':dataset,
             'partial':False} for i,n in enumerate(values)]

class TrendsResearchTests(unittest.TestCase):
    def test_sustained_surge_reports_country_keyword_and_change(self):
        rows=weekly('US','medicube',[18]*10+[44]*4)
        out=ts.detect(rows,[{'code':'US','name':'미국'}],today=DAY)
        self.assertEqual(out['detected_pairs'],1)
        alert=out['alerts'][0]
        self.assertEqual(alert['country'],'US')
        self.assertEqual(alert['country_name'],'미국')
        self.assertEqual(alert['keyword'],'medicube')
        self.assertEqual(alert['direction'],'관심도 상승')
        self.assertGreater(alert['change_pct'],100)
        self.assertEqual(alert['recent_points'],4)
        self.assertIn('0~100',alert['explanation'])

    def test_sustained_drop_is_not_zero_sales(self):
        rows=weekly('BR','AGE-R',[65]*10+[27]*4,dataset='BRAZIL')
        out=ts.detect(rows,[{'code':'BR','name':'브라질'}],today=DAY)
        self.assertEqual(out['detected_pairs'],1)
        self.assertEqual(out['alerts'][0]['direction'],'관심도 하락')
        self.assertEqual(out['alerts'][0]['keyword'],'AGE-R')
        self.assertIn('매출',out['source_note'])

    def test_single_spike_or_tiny_baseline_does_not_trigger(self):
        isolated=weekly('US','medicube',[25]*10+[25,25,25,95])
        noise=weekly('JP','low',[2]*10+[10]*4,'JPN')
        result=ts.detect(isolated+noise,today=DAY)
        self.assertEqual(result['detected_pairs'],0)

    def test_insufficient_stale_or_partial_weeks_are_ignored(self):
        short=weekly('US','medicube',[20]*7+[50]*4)
        stale=weekly('FR','medicube',[20]*10+[50]*4,
                     dataset='FRANCE',end=dt.date(2026,8,10))
        partial=weekly('CL','medicube',[20]*10+[50]*4,
                       dataset='CHILE')
        for x in partial[-4:]:
            x['partial']=True
        report=ts.detect(short+stale+partial,today=DAY)
        self.assertEqual(report['detected_pairs'],0)

    def test_never_combine_separately_normalized_datasets(self):
        old=weekly('US','medicube',[50]*10+[90]*4,'RUN_OLD',
                   end=dt.date(2026,11,1))
        latest=weekly('US','medicube',[45]*14,'RUN_NEW',
                      end=dt.date(2026,11,4))
        result=ts.detect(old+latest,today=DAY)
        self.assertEqual(result['detected_pairs'],0)

if __name__=='__main__':unittest.main()
