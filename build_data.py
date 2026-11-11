#!/usr/bin/env python3
"""Zero-key GitHub Actions data collector for the static APR investment terminal.

No manufactured market points, no paywalled APIs, no auth bypasses.
Failures retain last verified figures + expose stale status.
"""
from __future__ import annotations
import csv
import os
import datetime as dt
import email.utils
from html import unescape
from html.parser import HTMLParser
import io
import json
import re
import sys
import time
import urllib.error
from pathlib import Path
from urllib import parse, request
import xml.etree.ElementTree as ET
from indicator_engine import calculate
import update_data
from optional_free_api import Budget, update_trends, update_amazon
from top100_tracker import track_bestsellers
from scrapedo_bestsellers import track_scrapedo
from retail_reference_collector import collect as refresh_retail_references
from news_localizer import localize_items, FIELD_KEYS
from financial_engine import update as refresh_financials
from trend_signals import detect as detect_trend_shifts

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data';IMPORTS=ROOT/'imports'
UA='APR-Market-Research/1.0 (personal investment dashboard, public data only)'
START='2026-05-01'
NOW=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
errors=[]

def read_json(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def save(name,value):
    path=DATA/name;path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)

def fetch(url,timeout=18):
    req=request.Request(url,headers={'User-Agent':UA,'Accept':'application/json, application/rss+xml, text/html, */*'})
    with request.urlopen(req,timeout=timeout) as r:return r.read(500000)

def load_csv(name):
    path=IMPORTS/name
    if not path.exists():return []
    with path.open('r',encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def safe_num(x,lo=0,hi=1e15):
    try:
        v=float(str(x).replace(',','').replace('$','').replace('%','').strip())
        return v if lo<=v<=hi else None
    except (TypeError,ValueError):return None

def valid_url(s,official=None):
    if not s:return False
    u=parse.urlparse(s)
    return u.scheme=='https' and bool(u.netloc) and (not official or u.hostname in official)


def collect_market(*, refresh_fx=True, refresh_freight=True):
    old=read_json(DATA/'data.json',{})
    try:
        market=update_data.update(DATA, refresh_fx=refresh_fx, refresh_freight=refresh_freight)
    except Exception as e:
        errors.append('주가/FX: '+str(e)[:260])
        market=old
    if not market or not market.get('series'):
        market={'meta':{'errors':['주가 데이터 확인 불가'],'complete':False},'series':[],'fx':[],'logistics':{'sea':[],'air':[]}}
    save('market.json',market)
    ta=calculate(market.get('series',[]))
    if ta['last'] and market.get('meta',{}).get('stock_last'):
        ta['last']['source']=market['meta'].get('stock_source','확인되지 않음')
    save('technical.json',ta)
    return market,ta


def collect_kbty():
    previous=read_json(DATA/'kbty.json',{})
    official='https://www.gafunds.com/kbty/'
    doc=None
    try:doc=unescape(fetch(official).decode('utf-8',errors='replace'))
    except Exception as ex:errors.append('KBTY 운용사 확인: '+str(ex)[:120])
    # Prospectus has been filed, but registration != actual trading.
    state={
      'updated_at':NOW, 'official_url':official,
      'sec_url':'https://www.sec.gov/Archives/edgar/data/919160/000121390026113359/ea0306550-01_485bpos.htm',
      'fund':'Guinness Atkinson K-Beauty ETF','ticker':'KBTY','exchange':'NYSE Arca',
      'expense_ratio_pct':0.55,'index':'Indxx K-Beauty Index','holdings_count_intended':25,
      'status':'현재 거래·상장 상태 미확인', 'launch_expected':None,
      'latest_price_usd':None,'price_date':None,'aum_usd':None,'nav_usd':None,
      'apr_weight_pct':None,'apr_shares':None,'apr_holding_as_of':None,
      'source_note':'가격: Yahoo Finance 비공식 일별시세. AUM: 운용사 페이지 제한적 추출 또는 출처 기록 CSV. NAV·APR 보유비중·보유주식수: 수동 검증 CSV 입력(자동 수집 아님). 미확인 항목은 null.',
      'price_history':previous.get('price_history',[]),'aum_history':previous.get('aum_history',[]),
      'holdings':previous.get('holdings',[]),'errors':[]
    }
    if doc:
        text=re.sub(r'<[^>]+>',' ',doc)
        text=re.sub(r'\s+',' ',text)
        if 'expected to begin trading in the second week of November' in text:
            state['status']='11월 둘째 주 상장 예정 문구 확인 (공식 사이트)'
            state['launch_expected']='11월 둘째 주 (현재 공식 페이지 문구, 변경 가능)'
        elif 'Launching November 2026' in text or 'Coming soon' in text:
            state['status']='출시 준비 중 (공식 사이트)'
        # Optional official net-assets extraction, ONLY inside Fund facts block.
        facts=re.search(r'Fund facts(.{0,3500}?)Performance',text,re.I)
        if facts:
            m=re.search(r'Net assets\s*\$\s*([\d,.]+)\s*([MB])?',facts.group(1),re.I)
            if m:
                n=safe_num(m.group(1))
                if n:state['aum_usd']=n*({'M':1e6,'B':1e9}.get((m.group(2) or '').upper(),1))
    else:
        state['status']='운용사 사이트 접근 실패 / 현재 거래 여부 미확인'
        for k in ('aum_usd','nav_usd','apr_weight_pct','apr_shares','apr_holding_as_of','latest_price_usd','price_date'):
            state[k]=previous.get(k)
    # Public Yahoo price chart: it is a *fallback price source*, not an official ETF fact.
    try:
        j=json.loads(fetch('https://query1.finance.yahoo.com/v8/finance/chart/KBTY?range=6mo&interval=1d').decode())
        c=j['chart']['result'][0];q=c['indicators']['quote'][0]
        dates=c.get('timestamp',[])
        new=[]
        for ts,val in zip(dates,q.get('close',[])):
            if val is None or not 1<float(val)<1000:continue
            date=dt.datetime.fromtimestamp(ts,dt.timezone.utc).date().isoformat()
            new.append({'date':date,'close_usd':round(float(val),4),'source':'Yahoo Finance 비공식 일별시세'})
        history={r['date']:r for r in state['price_history'] if r.get('date') and r.get('close_usd')}
        history.update({r['date']:r for r in new})
        state['price_history']=[history[d] for d in sorted(history)]
        if state['price_history']:
            last=state['price_history'][-1]
            state['latest_price_usd']=last['close_usd'];state['price_date']=last['date']
            state['status']='거래가격 관측 (운용사에서 상장 여부 확인 필요)' if not doc or 'expected to begin' not in doc else '거래가격 관측 / 운용사 상장예정 안내 확인 필요'
    except Exception as e:
        state['errors'].append('KBTY 비공식 주가 미확인: '+str(e)[:120])
    # AUM & holdings from verifiable official-source CSV (user-provided record, never simulated).
    aum_items=[]
    for r in load_csv('kbty_aum.csv'):
        n=safe_num(r.get('aum_usd'),10000,1e13)
        if not (re.fullmatch(r'20\d\d-\d\d-\d\d',r.get('date','')) and n and valid_url(r.get('source_url',''))):continue
        aum_items.append({'date':r['date'],'aum_usd':n,'nav_usd':safe_num(r.get('nav_usd'),0.01,10000),
                          'shares_outstanding':safe_num(r.get('shares_outstanding'),0,1e12),'source_url':r['source_url']})
    if aum_items:
        hist={x['date']:x for x in state['aum_history'] if x.get('date')}
        hist.update({x['date']:x for x in aum_items})
        state['aum_history']=[hist[k] for k in sorted(hist)]
        v=state['aum_history'][-1];state['aum_usd']=v['aum_usd'];state['nav_usd']=v['nav_usd']
    holdings=[]
    for r in load_csv('kbty_holdings.csv'):
        wt=safe_num(r.get('weight_pct'),0,100)
        if not (re.fullmatch(r'20\d\d-\d\d-\d\d',r.get('as_of','')) and wt is not None and valid_url(r.get('source_url',''))):continue
        holdings.append({'as_of':r['as_of'],'ticker':r.get('ticker',''),'name':r.get('name',''),
                         'weight_pct':wt,'shares':safe_num(r.get('shares'),0,1e12),'source_url':r['source_url']})
    if holdings:
        latest=max(x['as_of'] for x in holdings)
        state['holdings']=[x for x in holdings if x['as_of']==latest]
    current=state['holdings'];has_holdings=bool(current)
    if has_holdings:
        candidates=[x for x in current if (x.get('ticker','').strip().upper() in ('278470','278470.KS') or
                                             x.get('name','').strip().upper() in ('APR','APR CORPORATION','에이피알'))]
        if candidates:
            state['apr_weight_pct']=sum(x['weight_pct'] for x in candidates)
            state['apr_shares']=sum(x['shares'] for x in candidates if x['shares'] is not None) or None
            state['apr_holding_as_of']=current[0]['as_of']
        else:
            # Confirmed complete list? CSV might be partial; do not assert APR 0%.
            state['apr_weight_pct']=None
            state['apr_holding_as_of']=None
    save('kbty.json',state)
    return state

NEWS_QUERIES=[
  # United States: keep APR/Medicube explicit to avoid generic K-beauty headlines.
  {'tag':'미국 오프라인 유통','country':'US','q':'"medicube" (Costco OR Ulta OR Target OR Walmart OR CVS OR Nordstrom)','hl':'en-US','gl':'US','ceid':'US:en'},
  {'tag':'미국 Amazon·온라인','country':'US','q':'"medicube" (Amazon OR "Prime Day" OR "TikTok Shop")','hl':'en-US','gl':'US','ceid':'US:en'},
  {'tag':'미국 뷰티기기·신제품','country':'US','q':'"medicube" ("AGE-R" OR "Booster Pro" OR "beauty device" OR PDRN)','hl':'en-US','gl':'US','ceid':'US:en'},
  {'tag':'브라질 메디큐브','country':'BR','q':'"medicube" beleza Brasil mercado','hl':'pt-BR','gl':'BR','ceid':'BR:pt-419'},
  {'tag':'아르헨티나 메디큐브','country':'AR','q':'"medicube" skincare Argentina','hl':'es-419','gl':'AR','ceid':'AR:es-419'},
  {'tag':'칠레 스킨부스터','country':'CL','q':'"medicube" "Kinegun" OR "skin booster" Chile','hl':'es-419','gl':'CL','ceid':'CL:es-419'},
  {'tag':'칠레 스킨부스터','country':'CL','q':'"medicube" "polinucleótidos" Chile','hl':'es-419','gl':'CL','ceid':'CL:es-419'},
  {'tag':'칠레 클리닉','country':'CL','q':'("Rejuran" OR "PN") "clínica" Santiago Chile','hl':'es-419','gl':'CL','ceid':'CL:es-419'},
  {'tag':'일본·중동 스킨부스터','country':'AE','q':'"medicube" "skin booster" Dubai OR UAE','hl':'en','gl':'AE','ceid':'AE:en'},
  {'tag':'일본·중동 스킨부스터','country':'SA','q':'"medicube" "skin booster" Saudi','hl':'en','gl':'SA','ceid':'SA:en'},
  {'tag':'의료기기 HIFU·RF','country':'KR','q':'에이피알 HIFU RF 의료기기 허가 출시','hl':'ko','gl':'KR','ceid':'KR:ko'},
  {'tag':'KBTY ETF','country':'US','q':'"KBTY" "Guinness" ETF','hl':'en','gl':'US','ceid':'US:en'},
]

def us_news_headline_relevant(title, category):
    """US-locale RSS can include global/generic articles; title must support tag.

    Country is target market, not the nationality of the publishing outlet.
    Keep brand-relevant reporting, and omit Canada-only headlines from US news.
    """
    if not str(category).startswith('미국 '):
        return True
    headline=str(title or '').rsplit(' - ',1)[0]
    if not re.search(r'\b(medicube|APR|AGE[- ]?R)\b|메디큐브|에이피알',headline,re.I):
        return False
    if (re.search(r'\b(Canada|Canadian|Shoppers Drug Mart)\b',headline,re.I)
        and not re.search(r'\b(US|U\.S\.|United States|American)\b',headline,re.I)):
        return False
    if category=='미국 오프라인 유통':
        return bool(re.search(r'\b(Ulta|Target|Walmart|Costco|CVS|Nordstrom|stores?|retail)\b',headline,re.I))
    if category=='미국 Amazon·온라인':
        return bool(re.search(r'\b(Amazon|Prime|TikTok|sale|deals?|discount|off)\b',headline,re.I))
    return True


def collect_news():
    previous=read_json(DATA/'news.json',{})
    fresh=[]
    for item in NEWS_QUERIES:
        query='https://news.google.com/rss/search?'+parse.urlencode({'q':item['q'],'hl':item['hl'],'gl':item['gl'],'ceid':item['ceid']})
        try:
            xml=ET.fromstring(fetch(query,timeout=12))
            for r in xml.findall('./channel/item')[:12]:
                title=r.findtext('title','').strip();url=r.findtext('link','').strip()
                if not title or not valid_url(url) or not us_news_headline_relevant(title,item['tag']):continue
                raw=r.findtext('pubDate','')
                try:date=email.utils.parsedate_to_datetime(raw).date().isoformat()
                except Exception:date=None
                if date and date<'2026-05-01':continue
                fresh.append({'title':title[:250],'url':url,'published':date,'category':item['tag'],'country':item['country'],
                              'classification':'관련 기사 — 미검증 (매출·인허가 확정 아님)','discovered_at':NOW})
        except Exception as e:errors.append('뉴스 '+item['tag']+': '+str(e)[:120])
    old=previous.get('items',[])
    merged={(x['url'],x.get('category')):x for x in old
            if x.get('url') and us_news_headline_relevant(x.get('title'),x.get('category'))}
    for item in fresh:
        key=(item['url'],item['category'])
        old_entry=merged.get(key)
        if old_entry and old_entry.get('title')==item['title']:
            # RSS refresh must not delete an already saved Korean translation.
            for name in FIELD_KEYS:
                if old_entry.get(name):
                    item[name]=old_entry[name]
        merged[key]=item
    items=sorted(merged.values(),key=lambda x:x.get('published') or '0000',reverse=True)[:180]
    items,korean_status=localize_items(items)
    status='이번 수집 신규 '+str(len(fresh))+'건' if fresh else '새 기사 수집 실패 또는 결과 없음 — 이전 저장값만 유지'
    package={'updated_at':NOW,'status':status,'items':items,
             'korean_digest':korean_status,
             'verified_events':read_json(ROOT/'config/verified_events.json',[]),
             'source_note':('Google News RSS의 제목과 원문 링크를 한글로 정리합니다. '
                            '한국어 요약은 제목 기반이며 기사 전문의 요약이 아닙니다. '
                            '실제 발주·매출·허가와 구별해 읽어야 합니다.')}
    save('news.json',package)
    return package


def collect_demand():
    config=read_json(ROOT/'config/markets.json',{})
    prev=read_json(DATA/'demand.json',{})
    trend=[];statuses=[]
    for f in sorted((IMPORTS/'trends').glob('*.csv')):
        mo=re.match(r'^([A-Z]{2})_(.+)\.csv$',f.name)
        if not mo:continue
        country=mo.group(1)
        if country not in {x['code'] for x in config.get('markets',[])}:continue
        try:
            with f.open(encoding='utf-8-sig',newline='') as inp:lines=list(csv.reader(inp))
            headeridx=next(i for i,r in enumerate(lines[:25]) if r and r[0].strip().lower() in ('day','week','month','date','날짜','주','월','일','주간','월간'))
            names=[re.sub(r':.*$','',str(x)).strip() for x in lines[headeridx][1:]]
            batch=[]
            for r in lines[headeridx+1:]:
                if not r:continue
                ds=re.match(r'(20\d\d-\d\d-\d\d)',r[0].strip())
                if not ds or ds.group(1)<START:continue
                for i,label in enumerate(names,1):
                    if i>=len(r):continue
                    val=safe_num(r[i],0,100)
                    if val is not None:
                        batch.append({'date':ds.group(1),'country':country,'term':label,'index':val,
                                      'source':'Google Trends 공식 CSV','dataset':f.name})
            if batch:trend.extend(batch);statuses.append(f'{f.name}: {len(batch)}개')
        except Exception as e:errors.append(f'Trends {f.name}: {str(e)[:110]}')
    if not trend:trend=prev.get('trends',[])
    api_key=os.environ.get('APISH_KEY','').strip()
    scrape_token=os.environ.get('SCRAPEDO_TOKEN','').strip()
    budget=Budget(api_key)
    api_count=0
    if api_key:
        trend,replaced=update_trends(budget,config,trend)
        if replaced:statuses.append(f'API.SH Google Trends: {replaced}개국 검색지수 새로고침')
        api_count+=replaced
    else:
        statuses.append('APISH_KEY 미설정 — API 자동 수집 비활성 (CSV 이용 가능)')
    # Verified BSR observations CSV; no invention or fabricated ASINs.
    amazon=[]
    for r in load_csv('amazon_observations.csv'):
        cc=r.get('country','').upper();asin=r.get('asin','').upper()
        n=safe_num(r.get('bsr'),1,1e8)
        if (cc not in {x['code'] for x in config.get('markets',[]) if x.get('amazon')} or
            not re.fullmatch(r'[A-Z0-9]{10}',asin) or not re.fullmatch(r'20\d\d-\d\d-\d\d',r.get('date','')) or not n or
            not valid_url(r.get('source_url',''))):continue
        amazon.append({'date':r['date'],'country':cc,'product':r.get('product',''),'asin':asin,'bsr':int(n),
                       'category':r.get('category',''),'reviews':safe_num(r.get('reviews')),'price':safe_num(r.get('price')),
                       'source_url':r.get('source_url'),'source':'사용자 확인·출처 URL 기록'})
    for x in prev.get('amazon',[]):
        if not any((x.get('date'),x.get('country'),x.get('asin'))==(y['date'],y['country'],y['asin']) for y in amazon):amazon.append(x)
    amazon.sort(key=lambda x:x.get('date',''))
    # Best-effort anonymous Amazon BSR; bounded requests, avoid CAPTCHA circumvention.
    watched=load_csv('amazon_watchlist.csv')
    # Reuse explicitly verified ASINs from Beauty list observations as a free
    # discovery source. Product rank calls are still cost-capped separately.
    for snapshot in prev.get('top100',[]):
        cc=snapshot.get('country','')
        for item in snapshot.get('medicube_listings',[]):
            asin=str(item.get('asin','')).upper()
            if re.fullmatch(r'[A-Z0-9]{10}',asin):
                watched.append({'country':cc,'asin':asin,
                    'product':item.get('title','')[:100]})
    auto_status=[]
    for r in ([] if api_key else watched[:12]):
        cc=r.get('country','').upper();asin=r.get('asin','').upper()
        market=next((x for x in config.get('markets',[]) if x['code']==cc and x.get('amazon')),None)
        if not market or not re.fullmatch('[A-Z0-9]{10}',asin):continue
        url='https://www.'+market['amazon']+'/dp/'+asin
        try:
            html=fetch(url,timeout=10).decode('utf-8',errors='ignore')
            if re.search('captcha|robot check|automated access',html,re.I):raise ValueError('자동 접근 차단')
            txt=unescape(re.sub(r'<[^>]+>',' ',html))
            mt=re.search(r'(Best Sellers Rank|Bestsellers Rank|Bestseller-Rang|Classement des meilleures ventes|Classifica Bestseller|ترتيب الأفضل مبيعاً).{0,180}?[#＃]\s*([\d,\.\s]{1,14})',txt,re.I|re.S)
            if not mt:raise ValueError('BSR 확인 불가')
            rank=int(re.sub(r'\D','',mt.group(2)))
            if not 1<=rank<=1e8:raise ValueError('BSR 비정상')
            today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
            k=(today,cc,asin)
            amazon=[x for x in amazon if (x.get('date'),x.get('country'),x.get('asin'))!=k]
            amazon.append({'date':today,'country':cc,'product':r.get('product',''),'asin':asin,'bsr':rank,
                           'category':'자동 추출·카테고리 미검증','source_url':url,'source':'아마존 공개 페이지 (자동 확인, 카테고리 재검증 권장)'})
            auto_status.append(f'{cc} {asin}: BSR #{rank}')
        except Exception as e:auto_status.append(f'{cc} {asin}: 확인 실패 ({str(e)[:65]})')
        time.sleep(.6)
    # When a free key is configured, verified cross-market ASIN discovery + BSR lookup.
    if api_key and not scrape_token:
        # Legacy fallback only: API.SH product BSR is often absent. Do not
        # spend product credits when Scrape.do is configured.
        amazon,discovered,count=update_amazon(budget,config,amazon,watched)
        api_count+=count
        auto_status.append(f'API.SH 보조 상품 BSR {count}건 확인')
    else:
        discovered=read_json(DATA/'discovered_asins.json',[])
        if scrape_token:
            auto_status.append('Scrape.do 모드: API.SH 개별 상품 BSR 호출 생략')
    if api_key:
        auto_status.append(f'API.SH 당월 예약 {budget.stats["attempted_credits"]}/750 크레딧')
        for err in budget.errors[:5]:errors.append('무료 API: '+err)
    # Separate from product BSR. Scrape.do provides ranked ASINs 1-100;
    # ranks without a confirmed brand/title MUST remain unidentified.
    top100_history=prev.get('top100',[])
    top100_status=[]
    scrape_credits=None
    if scrape_token:
        try:
            top100_history,notes,_,scrape_credits=track_scrapedo(
                scrape_token,config,top100_history,amazon)
            top100_status.extend(notes)
        except Exception as exc:
            top100_status.append('Scrape.do 수집 실패: '+type(exc).__name__)
            errors.append('Scrape.do 순위 수집 예외: '+type(exc).__name__)
    if api_key:
        try:
            top100_history,notes,_=track_bestsellers(budget,config,top100_history)
            top100_status.extend(notes)
        except Exception as exc:
            top100_status.append('API.SH Top 100 관측 실패: '+type(exc).__name__)
            errors.append(top100_status[-1])
    elif not scrape_token:
        top100_status.append('무료 API 키 미설정 — Top 100 자동 수집 보류')
    # Rankings observed inside a verified Beauty bestseller page ARE a
    # product's Beauty-category BSR for that date. Make them visible on the
    # product chart even when separate Amazon Product API returns no results.
    known={(x.get('date'),x.get('country'),x.get('asin')) for x in amazon}
    for snap in top100_history:
        if snap.get('category')!='beauty' or not snap.get('date'):
            continue
        market=next((z for z in config.get('markets',[])
                     if z.get('code')==snap.get('country') and z.get('amazon')),None)
        if not market:
            continue
        for item in snap.get('medicube_listings',[]):
            asin=str(item.get('asin','')).upper()
            rank=item.get('rank')
            try:rank=int(rank)
            except (TypeError,ValueError):continue
            key=(snap['date'],snap['country'],asin)
            if not re.fullmatch(r'[A-Z0-9]{10}',asin) or not 1<=rank<=100 or key in known:
                continue
            title=str(item.get('title') or 'medicube '+asin)
            lower=title.lower()
            if 'zero pore pad' in lower:product='medicube zero pore pad'
            elif 'pink peptide serum' in lower:product='medicube PDRN pink peptide serum'
            elif 'collagen jelly cream' in lower:product='medicube collagen jelly cream'
            elif 'night wrapping' in lower:product='medicube collagen night wrapping mask'
            elif 'booster pro' in lower:product='medicube AGE-R booster pro'
            else:product=title[:95]
            amazon.append({'date':snap['date'],'country':snap['country'],
                'product':product,'title':title,'asin':asin,'bsr':rank,
                'category':'Beauty & Personal Care (전체 베스트셀러 카테고리)',
                'reviews':None,'price':None,
                'source_url':'https://www.'+market['amazon']+'/dp/'+asin,
                'source':'Amazon Beauty 베스트셀러 순위 관측('+('Scrape.do' if str(snap.get('source','')).startswith('Scrape.do') else 'API.SH')+')',
                'observed_coverage':snap.get('coverage_count'),
                'source_quality':'verified_list_rank'})
            known.add(key)
    # Separately observed, category-specific PDP BSR: never assume this is
    # the Beauty Top100 position and never fabricate missing historical ranks.
    pdp_rows=read_json(DATA/'scrapedo_pdp.json',[])
    if isinstance(pdp_rows,list):
        present={(x.get('date'),x.get('country'),x.get('asin'),x.get('category'),
                  x.get('source_quality')) for x in amazon}
        valid_countries={x['code'] for x in config.get('markets',[]) if x.get('amazon')}
        for row in pdp_rows:
            if not isinstance(row,dict):continue
            cc=row.get('country');asin=str(row.get('asin','')).upper()
            day=row.get('date');category=str(row.get('category',''))
            rank=safe_num(row.get('bsr'),1,1e8)
            k=(day,cc,asin,category,'verified_product_rank')
            if (cc not in valid_countries or
                not re.fullmatch(r'[A-Z0-9]{10}',asin) or
                not re.fullmatch(r'20\\d\\d-\\d\\d-\\d\\d',str(day)) or
                not category or rank is None or k in present):continue
            record=dict(row)
            record['bsr']=int(rank)
            amazon.append(record);present.add(k)
    amazon.sort(key=lambda x:(x.get('date',''),x.get('country',''),x.get('bsr',999999)))
    for err in budget.errors[:5]:
        msg='무료 API: '+err
        if msg not in errors:errors.append(msg)
    retail=[]
    for r in load_csv('retail_observations.csv'):
        if not (re.fullmatch(r'20\d\d-\d\d-\d\d',r.get('date','')) and valid_url(r.get('source_url',''))):continue
        retail.append(r)
    if not retail:retail=prev.get('retail',[])
    output={'updated_at':NOW,'countries':config.get('markets',[]),'products':config.get('products',[]),
        'trends_terms':config.get('trends_terms',{}),'retailers':config.get('retailers',[]),
        'trends':trend,'trends_status':statuses or ['공식 CSV 데이터 없음 — Google Trends 원본 링크 이용'],
        'amazon':amazon[-10000:],'amazon_status':auto_status or ['등록된 검증 ASIN 없음 / 수집 전. BSR 자동 수집은 접근 제한 가능'],
        'top100':top100_history[-4000:], 'top100_status':top100_status,
        'scrapedo_reserved_credits':scrape_credits,
        'watchlist':[x for x in watched if x.get('asin')]+discovered,
        'retail':retail,'api_mode':('free_api_sh' if api_key else 'csv_or_public'),
        'api_credits_used_this_month':budget.stats.get('attempted_credits',0) if api_key else None,
        'note':'BSR=카테고리 내 판매 순위이지 판매량이 아님. Google Trends=국가·기간·검색 그룹 내 상대지수(0~100).'}
    save('demand.json',output)
    # Small independent verification record so rankings can be checked without
    # downloading the (potentially large) multi-country Google Trends series.
    save('top100.json',{'updated_at':NOW,'snapshots':top100_history[-4000:],
                        'status':top100_status,
                        'coverage_note':'Complete requires all ranks 1..100 AND all 100 products identified. Rank-only ASINs without title imply minimum confirmed count.',
                        'scrapedo_reserved_credits':scrape_credits})
    return output


def main():
    DATA.mkdir(exist_ok=True)
    market,technical=collect_market()
    kbty=collect_kbty()
    news=collect_news()
    demand=collect_demand()
    # Derived research: no extra external or paid API requests.
    try:
        financials=refresh_financials()
    except Exception as exc:
        financials=read_json(DATA/'financials.json',{})
        errors.append('재무자료 계산 실패: '+str(exc)[:140])
    try:
        trend_signals=detect_trend_shifts(demand.get('trends',[]),demand.get('countries',[]))
        save('trend_signals.json',trend_signals)
    except Exception as exc:
        trend_signals=read_json(DATA/'trend_signals.json',{})
        errors.append('Google Trends 변화 분석 실패: '+str(exc)[:140])
    apr_theses=read_json(DATA/'apr_theses.json',{})
    # Independent, free official-retailer snapshot collection. Its failures
    # retain the last verified values and do not block other market updates.
    try:
        retail_refs=refresh_retail_references()
    except Exception as exc:
        retail_refs={'status':'failed','failures':[str(exc)[:160]],'successes':[]}
    status={'generated_at_utc':NOW, 'timezone':'Asia/Seoul',
      'price_last':market.get('meta',{}).get('stock_last'),
      'price_coverage_start':market.get('meta',{}).get('coverage_start'),
      'fx_last':market.get('meta',{}).get('usd_fx_last'),
      'technical_last':technical.get('last',{}).get('date'),
      'technical_ohlc_days':technical.get('valid_high_low',0),
      'kbty_status':kbty['status'], 'news_count':len(news.get('items',[])),
      'trends_points':len(demand.get('trends',[])), 'amazon_points':len(demand.get('amazon',[])),
      'beauty_leaderboard_snapshots':len(demand.get('top100',[])),
      'retail_reference':retail_refs,
      'errors':errors+market.get('meta',{}).get('errors',[]),'data_policy':'모든 실측은 출처와 기준일 표시. 실패 시 이전값 유지·오류 표시.'}
    save('status.json',status)
    payload={'market':market,'technical':technical,'kbty':kbty,'news':news,'demand':demand,'status':status,
             'financials':financials,'trend_signals':trend_signals,'apr_theses':apr_theses}
    (DATA/'bootstrap.js').write_text('window.APR_BOOTSTRAP = '+json.dumps(payload,ensure_ascii=False,separators=(',',':'))+';\n',encoding='utf-8')
    print(json.dumps(status,ensure_ascii=False,indent=2))
    return 0

if __name__=='__main__':sys.exit(main())
