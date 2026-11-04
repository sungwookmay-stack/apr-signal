#!/usr/bin/env python3
"""Optional full-rank Amazon Beauty scraper using Scrape.do's free plan.

Read ranks 1-50 and 51-100. Amazon only publishes detailed title cards for
roughly 30 of each 50 ranks; unknown ASINs are NEVER assumed non-Medicube.

No paid plan, no retries, no proxy upgrade, no token in logs or public data.
The local budget reserves 3 credits per API request (provider publishes a
1-credit Amazon default). It deliberately stops below the free 1,000 cap.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from top100_tracker import make_snapshot, EXCLUSION, MEDICUBE, ASIN

ROOT=Path(__file__).resolve().parent
STATE=ROOT/'data/scrapedo_usage.json'
LOCAL_LIMIT=690
RESERVE_PER_CALL=3
API='https://api.scrape.do/plugin/amazon/bestsellers'

def load_json(p,default):
    try:return json.loads(Path(p).read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError):return default

def save_json(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

class FreeQuota:
    """Conservatively reserve more than provider's documented Amazon base cost."""
    def __init__(self,token,day=None):
        self.token=token
        self.day=day or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
        self.month=self.day.strftime('%Y-%m')
        self.stats=load_json(STATE,{})
        if self.stats.get('month')!=self.month:
            self.stats={'month':self.month,'reserved_credits':0,'calls':0,
                        'provider_credits_reported':0}
        self.errors=[]
    def can_call(self):
        return bool(self.token) and self.stats['reserved_credits']+RESERVE_PER_CALL<=LOCAL_LIMIT
    def get(self,domain,page):
        if not self.can_call():return None
        self.stats['reserved_credits']+=RESERVE_PER_CALL
        self.stats['calls']+=1
        self.stats['last_call_date']=self.day.isoformat()
        save_json(STATE,self.stats) # persist BEFORE network call (repeat runs cannot reset)
        params={'token':self.token,'category':'beauty','geocode':domain.lower(),
                'type':'bestsellers','page':page,'super':'false'}
        url=API+'?'+urllib.parse.urlencode(params)
        try:
            req=urllib.request.Request(url,headers={'Accept':'application/json','User-Agent':'APR-SIGNAL/1.0'})
            with urllib.request.urlopen(req,timeout=32) as response:
                raw=response.read(1300000)
                cost=response.headers.get('Scrape.do-Request-Cost')
                if cost:
                    try:self.stats['provider_credits_reported']+=int(cost)
                    except (ValueError,TypeError):pass
                remain=response.headers.get('Scrape.do-Remaining-Credits')
                if remain:
                    try:self.stats['provider_remaining_last']=int(remain)
                    except (ValueError,TypeError):pass
                save_json(STATE,self.stats)
            return json.loads(raw.decode('utf-8'))
        except urllib.error.HTTPError as ex:
            self.errors.append(f'{domain.upper()} page {page}: HTTP {ex.code}')
        except (TimeoutError,urllib.error.URLError,ValueError, OSError) as ex:
            # NEVER stringify an error URL: query contains the private API token.
            self.errors.append(f'{domain.upper()} page {page}: {type(ex).__name__}')
        return None

def _known_titles(history,verified_amazon):
    names={}
    for s in history:
        for p in s.get('medicube_listings',[]):
            asin=str(p.get('asin') or '').upper()
            title=str(p.get('title') or '')
            if ASIN.fullmatch(asin) and MEDICUBE.search(title) and not EXCLUSION.search(title):
                names[asin]=title
    for p in verified_amazon:
        asin=str(p.get('asin') or '').upper()
        title=str(p.get('title') or p.get('product') or '')
        if ASIN.fullmatch(asin) and MEDICUBE.search(title) and not EXCLUSION.search(title):
            names[asin]=title
    return names

def normalize_page(payload, page, known=None):
    """Join full 50 rank rows with about 30 title cards (by exact ASIN)."""
    if not isinstance(payload,dict):return None
    if str(payload.get('category') or '').lower() not in ('beauty','beauty-personal-care'):
        return None
    if str(payload.get('type') or 'bestsellers').lower() not in ('bestsellers','best_sellers'):
        return None
    if str(payload.get('page',page))!=str(page):return None
    ranks=payload.get('ranking')
    details=payload.get('products')
    if not isinstance(ranks,list) or not isinstance(details,list):
        return None
    known=known or {}
    by_asin={str(p.get('asin') or '').upper():p for p in details if isinstance(p,dict)}
    result=[]
    expected=range(1,51) if page==1 else range(51,101)
    for x in ranks:
        if not isinstance(x,dict):continue
        try:rnk=int(x.get('rank'))
        except (ValueError,TypeError):continue
        asin=str(x.get('asin') or '').upper()
        if rnk not in expected or not ASIN.fullmatch(asin):continue
        info=by_asin.get(asin,{})
        title=str(info.get('title') or known.get(asin) or '')[:180]
        brand=str(info.get('brand') or '')[:100]
        url=str(x.get('url') or info.get('url') or '')
        if not url.startswith('https://www.amazon.'):
            url='https://www.amazon.com/dp/'+asin
        result.append((rnk,asin,title,url,brand))
    return result

def track_scrapedo(token,config,history,verified_amazon=None,client=None):
    """US, UK each day; rotate one other marketplace, maximum 6 requests/day."""
    quota=client or FreeQuota(token)
    history=list(history or [])
    if not token:
        return history,['SCRAPEDO_TOKEN 미등록 — 기존 API.SH 사용'],0,0
    today=quota.day.isoformat()
    markets=[m for m in config.get('markets',[]) if m.get('amazon')]
    priority=[m for code in ('US','GB') for m in markets if m['code']==code]
    rest=[m for m in markets if m['code'] not in ('US','GB')]
    rotation=[rest[quota.day.toordinal()%len(rest)]] if rest else []
    chosen=priority+rotation
    names=_known_titles(history,verified_amazon or [])
    notes=[]
    added=0
    for m in chosen:
        cc=m['code']
        old_today=next((s for s in history if s.get('date')==today and s.get('country')==cc),None)
        if old_today and str(old_today.get('source','')).startswith('Scrape.do'):
            notes.append(f'{cc}: Scrape.do 당일 기록 재사용')
            continue
        pages=[]
        for page in (1,2):
            if not quota.can_call():
                notes.append('Scrape.do 월 무료 예산 보호 한도 도달')
                break
            payload=quota.get(cc,page)
            normalized=normalize_page(payload,page,names)
            if normalized is None:
                notes.append(f'{cc}: Beauty {page}페이지 응답 검증 실패')
                continue
            if normalized:
                pages.append(normalized)
        if not pages:continue
        snap=make_snapshot(cc,pages,today)
        snap['marketplace']=m['amazon']
        snap['source']='Scrape.do Amazon Best Sellers Beauty / 1..100 ranking + partial titles'
        snap['page_count']=len(pages)
        # A 100-rank chart does not imply every ASIN's brand is known.
        previous=next((s for s in reversed(history) if s.get('country')==cc and s.get('date')<today),None)
        if previous and previous.get('coverage_complete') and snap.get('coverage_complete'):
            a={p['asin'] for p in previous.get('medicube_listings',[])}
            b={p['asin'] for p in snap['medicube_listings']}
            snap['new_asins']=sorted(b-a);snap['exit_asins']=sorted(a-b)
            snap['new_count']=len(snap['new_asins'])
            snap['exit_count']=len(snap['exit_asins'])
        if old_today:
            quality=lambda v:(v.get('coverage_count',0),v.get('identity_coverage_count',0))
            if quality(old_today)>=quality(snap):
                notes.append(f'{cc}: 기존 관측 범위가 동등하거나 더 커서 보존')
                continue
            history=[h for h in history if not(h.get('country')==cc and h.get('date')==today)]
        history.append(snap);added+=1
        for p in snap['medicube_listings']:
            if p.get('title'):names[p['asin']]=p['title']
        notes.append(f"{cc}: 확인된 ASIN {snap['medicube_confirmed_count']}개 최소, "
                     f"순위 {snap['coverage_count']}/100, "
                     f"상품명 {snap['identity_coverage_count']}/100")
    notes.extend(quota.errors[:8])
    history.sort(key=lambda s:(s.get('date',''),s.get('country','')))
    return history[-500:],notes,added,quota.stats.get('reserved_credits',0)
