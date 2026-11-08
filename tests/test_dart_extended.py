"""Offline tests for official OpenDART and no-leakage owner/finance/capital collectors."""
import io, json, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
from urllib import parse

import dart_ownership as own
import dart_financials as fin
import dart_capital as cap
import retail_reviews as reviews


class FreeDartTests(unittest.TestCase):
    CODE='01234567'
    KEY='NEVER_REVEAL_TEST_DART_API_KEY'

    def test_exact_company_mapping(self):
        xml=('<result><list><corp_code>00000001</corp_code>'
             '<corp_name>다른회사</corp_name><stock_code>278469</stock_code></list>'
             '<list><corp_code>01234567</corp_code><corp_name>에이피알</corp_name>'
             '<stock_code>278470</stock_code></list></result>').encode()
        f=io.BytesIO()
        with zipfile.ZipFile(f,'w') as z:z.writestr('CORPCODE.xml',xml)
        self.assertEqual(own.resolve_corp_code(f.getvalue()),'01234567')

    def test_real_ownership_response_fields_and_reporter_scope(self):
        raw=[
            {'corp_code':self.CODE,'rcept_no':'20261109000001',
             'rcept_dt':'2026-11-09','repror':'최대주주 A',
             'stkqy':'1,000,000','stkqy_irds':'-1,000',
             'stkrt':'10.20','stkrt_irds':'-0.10',
             'report_tp':'변동','report_resn':'주식 매도'},
            {'corp_code':'00000001','rcept_no':'20261109000002',
             'rcept_dt':'2026-11-09','repror':'타사','stkqy':'99,000,000'}
        ]
        one=own.normalize('majorstock',raw,self.CODE)
        self.assertEqual(len(one),1)
        self.assertEqual(one[0]['ownership_pct'],10.2)
        self.assertEqual(one[0]['shares_change_reported'],-1000)
        self.assertEqual(one[0]['source_url'],
                         'https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261109000001')
        officer=own.normalize('elestock',[{
          'corp_code':self.CODE,'rcept_no':'20261109000003','rcept_dt':'20261109',
          'repror':'임원 B','sp_stock_lmp_cnt':'1200',
          'sp_stock_lmp_irds_cnt':'100','sp_stock_lmp_rate':'0.02',
          'sp_stock_lmp_irds_rate':'0.01'
        }],self.CODE)
        self.assertEqual(officer[0]['shares_reported'],1200)
        self.assertEqual(officer[0]['ownership_pct'],0.02)

    def test_financial_cfs_exact_account_and_interim_basis(self):
        base={'corp_code':self.CODE,'bsns_year':'2026','reprt_code':'11012',
              'currency':'KRW'}
        def line(sj,n,id,value,cumulative=None):
            return {**base,'sj_div':sj,'account_nm':n,'account_id':id,
                    'thstrm_amount':value,'thstrm_add_amount':cumulative}
        doc={'status':'000','list':[
          line('IS','매출액','ifrs-full_Revenue','2,000,000,000','3,500,000,000'),
          line('IS','영업이익','dart_OperatingIncomeLoss','400,000,000','600,000,000'),
          line('IS','당기순이익','ifrs-full_ProfitLoss','-15,000,000','100,000,000'),
          line('BS','재고자산','ifrs-full_Inventories','850,000,000'),
          line('CF','영업활동현금흐름','ifrs-full_CashFlowsFromUsedInOperatingActivities','990,000,000'),
          {**line('IS','매출액','ifrs-full_Revenue','999999'), 'corp_code':'99999999'}
        ]}
        r=fin.parse_api_response(doc,2026,'11012',self.CODE)
        self.assertEqual(r['accounts']['sales']['value_won'],2_000_000_000)
        self.assertEqual(r['accounts']['sales']['ytd_won'],3_500_000_000)
        self.assertEqual(r['accounts']['sales']['amount_basis'],'current_3months')
        self.assertEqual(r['accounts']['inventory']['value_won'],850_000_000)
        self.assertEqual(r['accounts']['net_income']['value_won'],-15_000_000)
        self.assertTrue(r['income_complete'],'Negative profit is a valid verified loss')
        self.assertEqual(fin.parse_api_response({'status':'013'},2026,'11012',self.CODE)['status'],
                         'no_disclosure')

    def test_dividend_and_treasury_total_and_no_duplicate_breakdown(self):
        items=[{'corp_code':self.CODE,'rcept_no':'20261109000004','stlm_dt':'2026-09-30',
                'se':'주당 현금배당금(원)','stock_knd':'보통주','thstrm':'1,000'},
               {'corp_code':'00000001','rcept_no':'20261109000004','stlm_dt':'2026-09-30',
                'se':'주당 현금배당금(원)','stock_knd':'보통주','thstrm':'99,999'}]
        div=cap.normalize('alotMatter',items,self.CODE,'2026Q3')
        self.assertEqual(len(div),1)
        self.assertEqual(div[0]['value'],1000)
        treas=cap.normalize('tesstkAcqsDspsSttus',[
           {'corp_code':self.CODE,'rcept_no':'20261109000005',
            'acqs_mth1':'소계','acqs_mth2':'직접취득',
            'acqs_mth3':'장내','stock_knd':'보통주','trmend_qy':'400'},
           {'corp_code':self.CODE,'rcept_no':'20261109000005',
            'acqs_mth1':'총계','acqs_mth2':'','acqs_mth3':'',
            'stock_knd':'보통주','trmend_qy':'600',
            'change_qy_acqs':'100','change_qy_dsps':'50',
            'change_qy_incnr':'0'}
        ],self.CODE,'2026Q3')
        self.assertEqual(len(treas),1)
        self.assertEqual(treas[0]['value'],600)
        self.assertEqual(treas[0]['shares_acquired_in_report'],100)

    def test_secret_never_persisted_in_dart_output(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ownership.json'
            p.write_text(json.dumps({'corp_code':self.CODE,'filings':[]}),encoding='utf-8')
            seen=[]
            def mock(url):
                seen.append(url)
                if 'majorstock.json' in url:return json.dumps({'status':'013'}).encode()
                if 'elestock.json' in url:return json.dumps({'status':'013'}).encode()
                raise AssertionError(url)
            out=own.refresh(key=self.KEY,transport=mock,output=p)
            self.assertTrue(out['ready'])
            self.assertEqual(len(seen),2)
            self.assertNotIn(self.KEY,p.read_text(encoding='utf-8'))
            self.assertNotIn(self.KEY,json.dumps(out))

    def test_item_review_snapshot_parsing_requires_exact_product(self):
        self.assertEqual(reviews.parse_product_reviews(
          'medicube Zero Pore Pad 3.9 195 Reviews', 'ulta'),
          {'rating':3.9,'reviews_count':195})
        self.assertEqual(reviews.parse_product_reviews(
          'medicube Zero Pore Pad 4.4 out of 5 stars with 141 reviews','target'),
          {'rating':4.4,'reviews_count':141})
        self.assertIsNone(reviews.parse_product_reviews('Other product 5.0 99999 Reviews','ulta'))
        self.assertIsNone(reviews.parse_product_reviews(
            'medicube Zero Pore Pad adjacent item 4.4 and 141 other products',
            'target'))

if __name__=='__main__':unittest.main()
