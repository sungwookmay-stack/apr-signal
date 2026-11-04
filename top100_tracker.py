#!/usr/bin/env python3
"""Snapshot confirmed medicube listings in Amazon Beauty best-seller pages.

API.SH documents about 50 items over two pages. This module NEVER calls a
partial listing a complete Top 100. A complete count needs ranks 1..100.
All requests use the shared Budget (750 attempted credits/month).
"""
from __future__ import annotations
import datetime as dt
import re

ASIN=re.compile(r'^[A-Z0-9]{10}$')
MEDICUBE=re.compile(r'(?<![a-z0-9])medicube(?![a-z0-9])|메디큐브',re.I)
EXCLUSION=re.compile(r'\b(compatible with|for medicube|fits medicube|replacement for medicube)\b',re.I)
EXPECTED_RANKS=set(range(1,101))

def is_medicube(item):
    brand=str(item.get('brand') or '')
    title=str(item.get('title') or '')
    if MEDICUBE.search(brand):
        return True
    return bool(MEDICUBE.search(title) and not EXCLUSION.search(title))

def extract_page(payload,expected_domain=None):
    """Return [(rank, asin, title, url, brand)] or None if category invalid."""
    if not isinstance(payload,dict):
        return None
    category=str(payload.get('category') or '').lower()
    if category and category not in ('beauty','beauty-personal-care','beauty-and-personal-care'):
        return None
    listname=str(payload.get('list') or 'best_sellers').lower()
    if listname not in ('best_sellers','bestsellers'):
        return None
    actual=str(payload.get('domain') or '').lower().removeprefix('www.').removeprefix('amazon.')
    if expected_domain and actual and actual != expected_domain:
        return None
    items=payload.get('items')
    if not isinstance(items,list):
        return None
    out=[]
    for obj in items:
        if not isinstance(obj,dict):
            continue
        rank=obj.get('rank')
        if isinstance(rank,bool):
            continue
        try:
            rank=int(str(rank).strip().replace('#',''))
        except (ValueError,TypeError):
            continue
        asin=str(obj.get('asin') or '').strip().upper()
        if rank not in EXPECTED_RANKS or not ASIN.fullmatch(asin):
            continue
        out.append((rank,asin,str(obj.get('title') or '')[:180],
                    str(obj.get('url') or ''),str(obj.get('brand') or '')))
    return out

def make_snapshot(country,pages,asof=None):
    """Only observed ranks count. Missing ranks never imply zero medicube products."""
    stamp=asof or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    ranks={}
    for page in pages:
        for rank,asin,title,url,brand in page:
            # Do not merge duplicate ASIN as separate products across pages.
            ranks.setdefault(rank,{'rank':rank,'asin':asin,'title':title,
                                   'url':url,'brand':brand})
    sorted_items=[ranks[k] for k in sorted(ranks)]
    rank_set=set(ranks)
    matched={}
    for item in sorted_items:
        if is_medicube(item):
            asin=item['asin']
            prev=matched.get(asin)
            if prev is None or item['rank']<prev['rank']:
                matched[asin]=item
    listings=sorted(matched.values(),key=lambda x:x['rank'])
    full=rank_set==EXPECTED_RANKS
    return {
        'date':stamp,'country':country,'category':'beauty',
        'category_scope':'Amazon Best Sellers > Beauty (country-specific)',
        'coverage_count':len(rank_set),'max_rank_observed':max(rank_set) if rank_set else None,
        'coverage_complete':full,'pages_received':len(pages),
        'medicube_confirmed_count':len(listings),
        'medicube_listings':listings,
        'rank_coverage':sorted(rank_set),
        'new_count':None,'exit_count':None,'new_asins':[],'exit_asins':[],
        'source':'API.SH Amazon Best Sellers /beauty, ASIN-based observed minimum',
        'note':('전체 1~100위 확인' if full else
                '부분 목록만 확보: 확인된 메디큐브 ASIN 최소 개수, 전체 Top 100 총수 아님')
    }

def track_bestsellers(client,cfg,previous):
    """US daily + two rotating other countries; 2 x 3 = <=6 credits/day."""
    history=list(previous or [])
    if not client.key:
        return history,['API 키 미설정 — Beauty 순위 자동 수집 미실행'],0
    today=client.today.isoformat()
    markets=[x for x in cfg.get('markets',[]) if x.get('amazon')]
    if not markets:
        return history,['아마존 마켓 없음'],0
    us=next((x for x in markets if x.get('code')=='US'),None)
    others=[x for x in markets if x.get('code')!='US']
    # Rotate other marketplaces fairly, two per day.
    start=(client.today.toordinal()*2)%len(others) if others else 0
    chosen=([us] if us else [])+([others[(start+i)%len(others)] for i in range(min(2,len(others)))])
    stats=[]
    snapshots=0
    for market in chosen:
        cc=market['code']
        if any(x.get('date')==today and x.get('country')==cc for x in history):
            stats.append(f'{cc}: 오늘 기록 존재 — 추가 API 호출 생략')
            continue
        domain=market['amazon'].removeprefix('amazon.')
        pages=[]
        for page in (1,2):
            if client.remaining()<1:
                stats.append(f'{cc}: 무료 예산 부족 — 수집 보류')
                break
            obj=client.get('amazon/v1/bestsellers',
                           {'category':'beauty','list':'best_sellers',
                            'page':page,'domain':domain,'raw':'0'},1)
            parsed=extract_page(obj,domain) if obj else None
            if parsed is None:
                stats.append(f'{cc}: Beauty {page}페이지 검증 실패 — 부분 기록')
                continue
            if parsed:
                pages.append(parsed)
            else:
                stats.append(f'{cc}: Beauty {page}페이지 실제 상품 미확인')
        if not pages:
            continue
        snap=make_snapshot(cc,pages,today)
        snap['marketplace']=market['amazon']
        previous_country=next((x for x in reversed(history) if x.get('country')==cc),None)
        if (previous_country and previous_country.get('pages_received')==2
            and snap['pages_received']==2
            and previous_country.get('rank_coverage')==snap.get('rank_coverage')):
            old_asins={x.get('asin') for x in previous_country.get('medicube_listings',[])}
            new_asins={x['asin'] for x in snap['medicube_listings']}
            snap['new_asins']=sorted(new_asins-old_asins)
            snap['exit_asins']=sorted(old_asins-new_asins)
            snap['new_count']=len(snap['new_asins'])
            snap['exit_count']=len(snap['exit_asins'])
        history.append(snap)
        snapshots+=1
        stats.append(f"{cc}: {snap['medicube_confirmed_count']}개 확인 / "
                     f"{snap['coverage_count']}개 순위 확인"
                     +(' · 완전' if snap['coverage_complete'] else ' · 부분'))
    history.sort(key=lambda x:(x.get('date',''),x.get('country','')))
    return history[-500:],stats,snapshots
