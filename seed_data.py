#!/usr/bin/env python3
"""Initialize honestly-labeled snapshots before the first online GitHub Action run."""
import datetime as dt
import json
from pathlib import Path
from indicator_engine import calculate
ROOT=Path(__file__).parent
DATA=ROOT/'data'

def read(p,default):
    try:return json.loads(p.read_text(encoding='utf-8'))
    except: return default

def write(name,x):
    (DATA/name).write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf-8')

market=read(DATA/'data.json',{})
if not (DATA/'market.json').exists():write('market.json',market)
if not (DATA/'technical.json').exists():write('technical.json',calculate(market.get('series',[])))
if not (DATA/'kbty.json').exists():write('kbty.json',{
 'updated_at':'2026-11-04T00:00:00+00:00',
 'official_url':'https://www.gafunds.com/kbty/',
 'sec_url':'https://www.sec.gov/Archives/edgar/data/919160/000121390026113359/ea0306550-01_485bpos.htm',
 'fund':'Guinness Atkinson K-Beauty ETF','ticker':'KBTY','exchange':'NYSE Arca',
 'expense_ratio_pct':0.55,'index':'Indxx K-Beauty Index','holdings_count_intended':25,
 'status':'2026년 11월 둘째 주 거래 개시 예정 (운용사 11월 4일 확인)',
 'launch_expected':'2026년 11월 둘째 주 (예정)',
 'latest_price_usd':None,'price_date':None,'aum_usd':None,'nav_usd':None,
 'apr_weight_pct':None,'apr_shares':None,'apr_holding_as_of':None,
 'price_history':[],'aum_history':[],'holdings':[],
 'source_note':'상장 전 공개된 운용사 자료, 실제 시세·AUM·편입비중은 확인될 때까지 공란',
 'errors':[]
})
if not (DATA/'news.json').exists():write('news.json',{
 'updated_at':'2026-11-04T00:00:00+00:00',
 'status':'실제 RSS 뉴스 수집 전 · 검증된 2026년 10월 3개 사건만 표시',
 'items':[],'verified_events':read(ROOT/'config/verified_events.json',[]),
 'source_note':'Google News RSS 실시간 수집은 GitHub Actions 첫 실행 후 시작'})
if not (DATA/'demand.json').exists():
    c=read(ROOT/'config/markets.json',{})
    write('demand.json',{'updated_at':'2026-11-04T00:00:00+00:00',
         'countries':c.get('markets',[]),'products':c.get('products',[]),
         'trends_terms':c.get('trends_terms',{}),'retailers':c.get('retailers',[]),
         'trends':[],'amazon':[],'retail':[],'watchlist':[],
         'trends_status':['API 연결 전 · 추이값 없음'],
         'amazon_status':['제품 ASIN 미확인 · API 연결 후 상품 검색 시작'],
         'api_mode':'csv_or_public','api_credits_used_this_month':None,
         'note':'BSR과 Trends 실측값 없음. 빈 그래프는 결측이며 0이 아님.'})
if not (DATA/'status.json').exists():write('status.json',{
 'generated_at_utc':'2026-11-04T00:00:00+00:00','timezone':'Asia/Seoul',
 'price_last':market.get('meta',{}).get('stock_last'),'price_coverage_start':market.get('meta',{}).get('coverage_start'),
 'fx_last':None,'technical_last':market.get('meta',{}).get('stock_last'),
 'technical_ohlc_days':0,'kbty_status':'상장 예정',
 'news_count':0,'trends_points':0,'amazon_points':0,
 'errors':['초기 동봉 데이터는 최근 50거래일 KRW 종가만 검증됨. 5월 이후 전체 및 FX는 첫 온라인 갱신 필요.'],
 'data_policy':'확인된 데이터만 표시. 미공개·수집 실패는 공란.'})
# file:// static open fallback; dates and sources stay visible even without API.
parts={n:read(DATA/(n+'.json'),None) for n in ('market','technical','kbty','news','demand','status')}
(DATA/'bootstrap.js').write_text('window.APR_BOOTSTRAP = '+json.dumps(parts,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
