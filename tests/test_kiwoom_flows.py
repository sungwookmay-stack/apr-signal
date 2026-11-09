"""No-network Kiwoom REST ka10059 tests; never leak credentials or invent pension."""
import datetime as dt
import unittest

from kiwoom_flows import (
    HOST, TOKEN_URL, DAILY_URL, _date, _to_integer, normalize_daily,
    get_token, fetch_investor_history, collect_if_connected
)


class KiwoomInvestorTests(unittest.TestCase):
    def test_missing_credentials_do_not_call_network(self):
        def forbidden(*a,**kw):
            raise AssertionError("network should not be called")
        result,meta=collect_if_connected(
            [{'date':'2026-11-06'}],appkey='',secretkey='',
            post=forbidden)
        self.assertEqual(result,[])
        self.assertEqual(meta['status'],'not_configured')

    def test_amounts_are_million_krw_and_pension_subset(self):
        data={'stk_invsr_orgn':[{
            'dt':'20261106','ind_invsr':'-1,200','frgnr_invsr':'+900',
            'orgn':'300','fnnc_invt':'100','penfnd_etc':'90',
            'samo_fund':'10','insrnc':'20','etc_fnnc':'0'
        }]}
        result=normalize_daily(data,permitted_dates={'2026-11-06'})
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['individual'],-1_200_000_000)
        self.assertEqual(result[0]['foreign'],900_000_000)
        self.assertEqual(result[0]['institution'],300_000_000)
        self.assertEqual(result[0]['pension'],90_000_000)
        self.assertEqual(result[0]['subgroups']['insurance'],20_000_000)
        self.assertEqual(result[0]['subgroups']['investment_trust'],None)
        self.assertEqual(result[0]['unit'],'KRW')

    def test_missing_pension_or_invalid_is_null(self):
        payload={'stk_invsr_orgn':[{
            'dt':'20261106','ind_invsr':'0','frgnr_invsr':'+5',
            'orgn':'-6','penfnd_etc':''
        }]}
        res=normalize_daily(payload)
        self.assertEqual(res[0]['individual'],0)
        self.assertIsNone(res[0]['pension'])
        self.assertEqual(_to_integer('N/A'),None)
        self.assertEqual(_to_integer('--123'),-123)
        self.assertIsNone(_to_integer('-'))
        self.assertEqual(_date('20261106'),'2026-11-06')

    def test_signed_fields_rejected_if_unusable(self):
        arr=normalize_daily({'stk_invsr_orgn':[
            {'dt':'20261106','ind_invsr':'unknown','frgnr_invsr':'?', 'orgn':'', 'penfnd_etc':None},
            {'dt':'20350101','ind_invsr':'600','orgn':'1'},
            {'dt':'20261106','ind_invsr':'-4','frgnr_invsr':'5', 'orgn':'-1'}
        ]},permitted_dates={'2026-11-06'})
        self.assertEqual(len(arr),1)
        self.assertEqual(arr[0]['individual'],-4_000_000)

    def test_token_failure_does_not_return_token_from_message(self):
        fake=lambda url,body,headers=None: (
            {'return_code':-1,'return_msg':'SECRET SERVER FAILURE',
             'token':'TEST_TOKEN'}, {})
        with self.assertRaises(RuntimeError) as cm:
            get_token('key','secret',post=fake)
        self.assertNotIn('secret',str(cm.exception).lower())
        self.assertNotIn('TEST_TOKEN',str(cm.exception))

    def test_request_pagination_million_and_read_only(self):
        calls=[]
        page1={'return_code':0,'stk_invsr_orgn':[
            {'dt':'20261106','ind_invsr':'-1','frgnr_invsr':'4',
             'orgn':'-3','penfnd_etc':'2'}]}
        page2={'return_code':'0','stk_invsr_orgn':[
            {'dt':'20261105','ind_invsr':'1','frgnr_invsr':'2',
             'orgn':'-2','penfnd_etc':'1'}]}
        def fake(url,body,headers=None):
            calls.append((url,body,headers))
            if url==TOKEN_URL:
                self.assertEqual(body['grant_type'],'client_credentials')
                self.assertEqual(body['appkey'],'A')
                self.assertEqual(body['secretkey'],'B')
                return {'return_code':0,'token':'MOCK_BEARER'},{}
            self.assertEqual(url,DAILY_URL)
            self.assertEqual(headers['authorization'],'Bearer MOCK_BEARER')
            self.assertEqual(headers['api-id'],'ka10059')
            self.assertEqual(body,{
                'dt':'20261106','stk_cd':'278470',
                'amt_qty_tp':'1','trde_tp':'0','unit_tp':'1'
            })
            if headers['cont-yn']=='N':
                self.assertEqual(headers['next-key'],'')
                return page1,{'cont-yn':'Y','next-key':'page2'}
            self.assertEqual(headers['cont-yn'],'Y')
            self.assertEqual(headers['next-key'],'page2')
            return page2,{'cont-yn':'N'}
        rows,status=fetch_investor_history(
            'A','B','2026-11-06',
            {'2026-11-06','2026-11-05'},post=fake)
        self.assertEqual([r['date'] for r in rows],
                         ['2026-11-05','2026-11-06'])
        self.assertEqual(rows[-1]['pension'],2_000_000)
        self.assertEqual(len(calls),3)
        self.assertEqual(status['status'],'ok')
        self.assertEqual(status['pages'],2)
        self.assertNotIn('MOCK_BEARER',str(status))
        self.assertTrue(status['read_only'])

    def test_partial_pagination_never_claimed_complete(self):
        def fake(url,body,headers=None):
            if url==TOKEN_URL:
                return {'return_code':0,'token':'MOCK'},{}
            return {'return_code':0,'stk_invsr_orgn':[
                    {'dt':'20261106','ind_invsr':'100'}]},{
                'cont-yn':'Y','next-key':'more'}
        rows,status=fetch_investor_history(
            'a','b','2026-11-06',{'2026-11-06'},
            post=fake,max_pages=1)
        self.assertEqual(len(rows),1)
        self.assertTrue(status['truncated'])
        self.assertEqual(status['status'],'partial_pagination')

    def test_unsupported_api_schema_stays_empty(self):
        def fake(url,body,headers=None):
            if url==TOKEN_URL:
                return {'return_code':0,'token':'MOCK'},{}
            return {'return_code':0},{}
        with self.assertRaises(ValueError):
            fetch_investor_history('a','b','2026-11-06',
                    {'2026-11-06'},post=fake)


if __name__=='__main__':
    unittest.main()
