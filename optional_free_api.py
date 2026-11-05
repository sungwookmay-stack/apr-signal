#!/usr/bin/env python3
"""Optional API.SH free-credit integration.

Uses only explicitly configured APISH_KEY from GitHub Actions secrets.
Hard ceiling of 750 *attempted* credits per UTC calendar month, below
provider's advertised 1,000 monthly free credits. This local limit is NOT a
billing guarantee; users must also set API.SH key spend caps/endpoint scope.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import time
from pathlib import Path
from urllib import parse, request

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'data/api_usage.json'
DISCOVER=ROOT/'data/discovered_asins.json'
BUDGET=750
UA='APR-Signal-PublicMarketResearch/1.0'


def read(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def save(path,doc):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(doc,ensure_ascii=False,indent=2),encoding='utf-8')

def number(x):
    try:
        if isinstance(x,bool):return None
        return float(str(x).replace(',','').replace('#','').strip())
    except (TypeError,ValueError):return None

class Budget:
    def __init__(self,token):
        self.key=token
        self.month=dt.datetime.now(dt.timezone.utc).strftime('%Y-%m')
        self.today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
        self.stats=read(STATE,{})
        if self.stats.get('month')!=self.month:
            self.stats={'month':self.month,'attempted_credits':0,'calls':0,'last_call':None}
        self.errors=[]
        self.count=0
    def remaining(self):return max(0,BUDGET-int(self.stats['attempted_credits']))
    def get(self,route,params,cost):
        if not self.key or self.remaining()<cost:return None
        # debit BEFORE network call, so retries/manual runs cannot bypass monthly limit
        self.stats['attempted_credits']+=cost;self.stats['calls']+=1
        self.stats['last_call']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
        save(STATE,self.stats)
        url='https://api.api.sh/'+route+'?'+parse.urlencode(params)
        headers={'User-Agent':UA,'x-api-key':self.key,'Accept':'application/json'}
        try:
            with request.urlopen(request.Request(url,headers=headers),timeout=36) as resp:
                j=json.loads(resp.read(800000).decode('utf-8'))
            if j.get('success') is False:
                raise ValueError(str(j.get('error','알 수 없는 API 오류'))[:140])
            self.count+=1
            return j
        except Exception as e:
            self.errors.append(f'{route}: {str(e)[:140]}')
            return None


def terms_for_country(cfg,country):
    look=cfg.get('trends_terms',{})
    if country in ('BR','AR','CL'):return look.get(country,[])[:5]
    if country in ('SA','AE','EG','QA','KW'):return look.get('ME',[])[:5]
    return look.get('default',[])[:5]


def update_trends(client,cfg,previous):
    """One full time series per country, replaced atomically per country.
    NEVER merge independent Trends 0-100 normalizations for same country.
    """
    old=previous or []
    grouped={x['code']:[] for x in cfg.get('markets',[]) if x.get('code')}
    for row in old:
        if row.get('source','').startswith('API.SH') and row.get('country') in grouped:
            grouped[row['country']].append(row)
    # Refresh all markets every other day, but also bootstrap newly added
    # countries even when today's scheduled collection has already finished.
    # Mark one attempt per missing country per day to avoid manual-run loops.
    today=client.today.isoformat()
    attempts=dict(client.stats.get('last_trends_attempt_by_country') or {})
    observed={r.get('country') for r in old if r.get('country')}
    missing={country for country in grouped
             if country not in observed and attempts.get(country)!=today}
    normal=((client.today.toordinal()%2==0) or not old) and client.stats.get('last_trends_run_day')!=today
    if not normal and not missing:return old,0
    if normal:
        client.stats['last_trends_run_day']=today
        save(STATE,client.stats)
    replaced=0
    # Pick a canonical single term set per country to preserve consistent comparisons.
    for market in cfg.get('markets',[]):
        country=market['code'];terms=terms_for_country(cfg,country)
        if not normal and country not in missing:continue
        if not terms or client.remaining()<1:continue
        attempts[country]=today
        client.stats['last_trends_attempt_by_country']=attempts
        save(STATE,client.stats)
        urlparams={'q':','.join(terms),'geo':country,
                   'time':f'2026-05-01 {client.today.isoformat()}',
                   'hl':'pt-BR' if country=='BR' else 'es-419' if country in ('AR','CL') else 'en-US',
                   'sections':'time','property':'web','raw':'0'}
        j=client.get('google-trends/v1/interest',urlparams,1)
        if not j or not isinstance(j.get('interest_over_time'),list):continue
        rows=[]
        for point in j['interest_over_time']:
            date=str(point.get('time') or '')[:10]
            if not re.fullmatch(r'20\d\d-\d\d-\d\d',date) or date<'2026-05-01':continue
            values=point.get('values') or {}
            if not isinstance(values,dict):continue
            for term in terms:
                v=number(values.get(term))
                if v is None or not 0<=v<=100:continue
                rows.append({'date':date,'country':country,'term':term,'index':int(v),
                             'partial':bool(point.get('partial')),
                             'source':'API.SH Google Trends 공공 검색지수',
                             'dataset':f'API.SH_{country}_{client.today.isoformat()}'})
        if rows:grouped[country]=rows;replaced+=1
    # Prefer user-imported Google Trends CSV when no API data for that country.
    csvrows=[x for x in old if not x.get('source','').startswith('API.SH')]
    ready={k for k,v in grouped.items() if v}
    return [r for r in csvrows if r.get('country') not in ready]+[r for rs in grouped.values() for r in rs],replaced


def canon_product(title,products):
    z=str(title).lower()
    if 'medicube' not in z and '메디큐브' not in z:return None
    rules=[('pink peptide',0),('pdrn',0),('zero pore',1),('collagen jelly',2),('night wrapping',3),('wrapping mask',3),('booster pro',4),('age-r booster',4)]
    for word,idx in rules:
        if word in z and idx<len(products):return products[idx]
    return None


def first_bsr(j):
    """Ranks can be absent on Amazon pages. Missing != zero and no fabricated rank."""
    ranks=j.get('best_sellers_rank',[])
    if isinstance(ranks,dict):ranks=[ranks]
    if not isinstance(ranks,list):return None
    for x in ranks:
        if isinstance(x,(int,float,str)):n=number(x);cat='카테고리 미제공'
        elif isinstance(x,dict):
            n=number(x.get('rank') or x.get('value') or x.get('position'))
            cat=str(x.get('category') or x.get('name') or '카테고리 미제공')[:90]
        else:continue
        if n is not None and 1<=n<=100000000:return int(n),cat
    return None


def update_amazon(client,cfg,old,watchlist):
    """One Amazon search per day (round-robin country) to discover actual ASINs.
    Two ranked-product checks per day (round-robin); 2*3*31=186 credits/month.
    Combined with Google Trends and Beauty leaderboard checks stays under 750 per month.
    """
    discovered=read(DISCOVER,[])
    marketlist=[x for x in cfg.get('markets',[]) if x.get('amazon')]
    if not marketlist:return old,discovered,0
    products=cfg.get('products',[])
    # One marketplace/day. Search returns ASINs and positions but not BSR.
    # Charge a CONSERVATIVE 3-credit reserve: API.SH Amazon pages currently disagree (1 vs 3).
    focus=marketlist[client.today.toordinal()%len(marketlist)]
    domain=focus['amazon'].removeprefix('amazon.')
    found=None
    if client.stats.get('last_amazon_search_day')!=client.today.isoformat():
        client.stats['last_amazon_search_day']=client.today.isoformat()
        save(STATE,client.stats)
        found=client.get('amazon/v1/search',{'q':'medicube','domain':domain,'raw':'0'},3)
    if found and isinstance(found.get('products'),list):
        for item in found['products'][:35]:
            asin=str(item.get('asin','')).upper()
            product=canon_product(item.get('title',''),products)
            if not product or not re.fullmatch(r'[A-Z0-9]{10}',asin):continue
            key=(focus['code'],product,asin)
            if not any((x.get('country'),x.get('product'),x.get('asin'))==key for x in discovered):
                discovered.append({'country':focus['code'],'product':product,'asin':asin,
                                   'title':str(item.get('title',''))[:140],
                                   'found_date':client.today.isoformat(),'source':'API.SH Amazon search'})
    discovered=discovered[-250:]
    save(DISCOVER,discovered)
    # Includes user-provided watchlist ASINs, which take precedence when duplicated.
    candidates=[]
    for x in [*watchlist,*discovered]:
        if not re.fullmatch(r'[A-Z0-9]{10}',str(x.get('asin','')).upper()):continue
        if not any(y.get('country')==x.get('country') and y.get('asin')==x.get('asin') for y in candidates):candidates.append(x)
    # Most recently updated items last; at most two product lookups per day.
    scored=[]
    for x in candidates:
        history=[y['date'] for y in old if y.get('country')==x['country'] and y.get('asin')==x['asin']]
        scored.append((max(history) if history else '2000-01-01',x))
    scored.sort(key=lambda v:v[0])
    added=0
    for _,x in [z for z in scored if z[0]!=client.today.isoformat()][:2]:
        if client.remaining()<3:break
        market=next((m for m in marketlist if m['code']==x['country']),None)
        if not market:continue
        asin=str(x['asin']).upper();domain=market['amazon'].removeprefix('amazon.')
        j=client.get('amazon/v1/product',{'url':asin,'domain':domain,'raw':'0'},3)
        if not j:continue
        title=j.get('title','')
        if 'medicube' not in str(title).lower() and '메디큐브' not in str(title):continue
        rank=first_bsr(j)
        if not rank:continue
        day=client.today.isoformat()
        record={'date':day,'country':x['country'],'product':x.get('product') or canon_product(title,products) or title[:80],
                'asin':asin,'bsr':rank[0],'category':rank[1],
                'reviews':number(j.get('rating_count')),
                'price':number(j.get('price_value')),
                'source_url':'https://www.'+market['amazon']+'/dp/'+asin,
                'source':'API.SH Amazon product · 공개 BSR 확인'}
        old=[r for r in old if (r.get('date'),r.get('country'),r.get('asin'))!=(day,record['country'],asin)]
        old.append(record);added+=1
    old.sort(key=lambda r:r.get('date',''))
    return old[-2000:],discovered,added
