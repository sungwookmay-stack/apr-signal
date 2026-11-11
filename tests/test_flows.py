"""APR institutional flow quality must not invent missing KRX, short or KSD values."""
import datetime as dt
import tempfile
import unittest
from pathlib import Path

from flows_engine import evaluate, month_data, refresh_saved_analysis
from flows_collect import (get_isin, normalize_investor_dataframe, merge_by_date,
                           normalize_short_dataframe, read_ksd)


def days(n=80, neg=False):
    start=dt.date(2026,5,1)
    rows=[]
    for i in range(n):
        price=100000+(i*(-100 if neg else 200))
        rows.append({'date':(start+dt.timedelta(days=i)).isoformat(),
                     'close_krw':price,'volume':1000000,
                     'high_krw':price+1000,'low_krw':price-1000})
    return rows


def flow_rows(prices, net=100_000_000):
    return [{'date':x['date'],'foreign':net,'institution':net,
             'pension':net//4,'individual':-2*net} for x in prices]


def technical(prices):
    return [{'date':x['date'],'close':x['close_krw'],
             'ma20':x['close_krw']-1000,'volume_ratio20':1.3}
            for x in prices]


class Row:
    def __init__(self, data):
        self.data=data
    def to_dict(self):
        return self.data


class Frame:
    empty=False
    def __init__(self, rows):
        self.rows=rows
    def iterrows(self):
        for d,row in self.rows:
            yield d,Row(row)


class FlowTests(unittest.TestCase):
    def test_isin_is_valid_for_known_samsung(self):
        self.assertEqual(get_isin('005930'),'KR7005930003')
        self.assertEqual(len(get_isin('278470')),12)

    def test_institution_pension_subset_not_double_counted(self):
        p=days(80)
        f=flow_rows(p)
        a=evaluate(p,f,technical_rows=technical(p))
        self.assertEqual(a['actors']['pension']['windows']['20']['net_krw'],500_000_000)
        self.assertEqual(a['actors']['institution']['windows']['20']['net_krw'],2_000_000_000)
        self.assertEqual(a['combined']['foreign_plus_inst_20d_krw'],4_000_000_000)
        self.assertEqual(a['combined']['level'],'positive')
        self.assertTrue(a['price_aligned'])

    def test_incomplete_window_withheld_not_zero_or_good(self):
        p=days(80)
        f=flow_rows(p[-12:])
        r=evaluate(p,f)
        self.assertIsNone(r['actors']['foreign']['windows']['20'])
        self.assertIsNone(r['actors']['foreign']['score'])
        self.assertEqual(r['combined']['level'],'unknown')

    def test_stale_date_never_good(self):
        p=days(80)
        r=evaluate(p,flow_rows(p[:-1]),technical_rows=technical(p))
        self.assertEqual(r['combined']['level'],'unknown')
        self.assertFalse(r['price_aligned'])

    def test_stale_common_date_keeps_reference_windows(self):
        p=days(80)
        r=evaluate(p,flow_rows(p[:-1]))
        self.assertEqual(r['combined']['level'],'unknown')
        ref=r['asof_analysis']
        self.assertEqual(ref['date'],p[-2]['date'])
        self.assertEqual(ref['lag_price_sessions'],1)
        self.assertEqual(ref['actors']['foreign']['windows']['20']['observed_days'],20)

    def test_asof_never_skips_missing_middle_day(self):
        p=days(80)
        f=flow_rows(p[:-1]); del f[-10]
        r=evaluate(p,f)
        self.assertIsNone(r['asof_analysis']['actors']['foreign']['windows']['20'])
        self.assertEqual(r['asof_analysis']['combined']['level'],'unknown')

    def test_offline_refresh_preserves_source_check_time(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); p=days(80)
            (root/'market.json').write_text(json.dumps({'series':p}))
            (root/'flows.json').write_text(json.dumps({
                'daily':flow_rows(p[:-1]),'checked_at_utc':'source-check',
                'data_status':{'source_status':'unchanged'}}))
            refresh_saved_analysis(root)
            saved=json.loads((root/'flows.json').read_text())
            self.assertEqual(saved['checked_at_utc'],'source-check')
            self.assertEqual(saved['data_status'],{'source_status':'unchanged'})
            self.assertEqual(saved['asof_analysis']['date'],p[-2]['date'])

    def test_no_asof_without_common_observation(self):
        self.assertIsNone(evaluate(days(80),[])['asof_analysis'])

    def test_no_redundant_asof_when_current(self):
        p=days(80)
        self.assertIsNone(evaluate(p,flow_rows(p))['asof_analysis'])

    def test_foreign_buying_while_price_falls_is_not_confirmed(self):
        p=days(80,neg=True)
        r=evaluate(p,flow_rows(p),technical_rows=technical(p))
        self.assertNotEqual(r['combined']['level'],'positive')
        self.assertIn('확인',r['combined']['detail'])

    def test_institution_and_foreign_disagree_stays_mixed(self):
        p=days(80)
        f=flow_rows(p)
        for row in f:
            row['institution']=-3_000_000_000
        a=evaluate(p,f)
        self.assertIn(a['combined']['level'],('weak','mixed'))

    def test_lending_and_reportable_short_balances_are_not_equivalent(self):
        p=days(80)
        short=[
          {'date':p[-2]['date'],'short_value_ratio_pct':5,
           'reported_net_short_balance_qty':120},
          {'date':p[-1]['date'],'short_value_ratio_pct':8,
           'reported_net_short_balance_qty':140}
        ]
        lending=[
          {'date':p[-2]['date'],'new_qty':200,'returned_qty':60,'balance_qty':3000},
          {'date':p[-1]['date'],'new_qty':100,'returned_qty':110,'balance_qty':2990}
        ]
        a=evaluate(p,flow_rows(p),short,lending)
        self.assertEqual(a['lending']['balance_change'],-10)
        self.assertEqual(a['short']['latest']['reported_net_short_balance_qty'],140)
        self.assertIsNone(a['short']['short_ratio_mean20_pct'])

    def test_krx_detailed_columns_are_net_krw_and_pension_subset(self):
        sample={
          '개인':-1234,'외국인':1000,'기타외국인':200,
          '금융투자':10,'보험':20,'투신':30,'사모':40,
          '은행':50,'기타금융':60,'연기금':70
        }
        data=normalize_investor_dataframe(Frame([('2026-11-06',sample)]))
        self.assertEqual(data[0]['foreign'],1200)
        self.assertEqual(data[0]['institution'],280)
        self.assertEqual(data[0]['pension'],70)
        self.assertEqual(data[0]['unit'],'KRW')

    def test_basic_krx_group_fallback_has_no_invented_pension(self):
        sample={'기관합계':1500000000,'외국인합계':-300000000,
                '개인':-1200000000,'기타법인':0}
        rows=normalize_investor_dataframe(
            Frame([('2026-11-06',sample)]),detail=False)
        self.assertEqual(rows[0]['foreign'],-300000000)
        self.assertEqual(rows[0]['institution'],1500000000)
        self.assertEqual(rows[0]['individual'],-1200000000)
        self.assertIsNone(rows[0]['pension'])
        self.assertFalse(rows[0]['institution_subgroup_covered'])

    def test_absent_KRX_detail_category_is_missing_not_zero(self):
        sample={'개인':2,'외국인':3,'연기금':1}
        rows=normalize_investor_dataframe(Frame([('2026-11-06',sample)]))
        self.assertIsNone(rows[0]['foreign'])
        self.assertIsNone(rows[0]['institution'])

    def test_merge_retains_priors_and_not_override_with_null(self):
        old=[{'date':'2026-11-06','foreign':100,'institution':50}]
        new=[{'date':'2026-11-06','foreign':None,'pension':4}]
        r=merge_by_date(old,new)
        self.assertEqual(r[0]['foreign'],100)
        self.assertEqual(r[0]['pension'],4)

    def test_missing_api_key_does_not_invent_ksd_lending(self):
        result,error=read_ksd('')
        self.assertEqual(result,[])
        self.assertIn('미등록',error)


if __name__=='__main__':
    unittest.main()
