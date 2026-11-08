#!/usr/bin/env python3
"""Best-effort official US retail product review counters (zero API keys).

Track rating and aggregate *count*, not review text, to avoid copyright or
personal-data replication. Only trust text from a product-specific official
page with the exact Medicube Zero Pore Pad heading; do not aggregate category
pages or interpret reviews as store POS sales. If a page is blocked, preserve
last records and mark the source as unavailable.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from pathlib import Path
from urllib import request

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'data/reference_signals.json'
PAGES={
  'target_zero_pore_95087437':{
    'retailer':'target','name':'Medicube Zero Pore Pad','product_id':'target_zero_pore_95087437',
    'url':'https://www.target.com/p/-/A-95087437'
  },
  'ulta_zero_pore_2645351':{
    'retailer':'ulta','name':'Medicube Zero Pore Pad','product_id':'ulta_zero_pore_2645351',
    'url':'https://www.ulta.com/p/zero-pore-pad-pimprod2053434?sku=2645351'
  }
}
USER_AGENT='Mozilla/5.0 (compatible; Independent APR Stock Tracker public product-counter research)'

def visible_text(html):
    # Delegate to existing HTML parser, stripping scripts/JSON fragments.
    from retail_reference_collector import text_of
    return text_of(html)

def parse_product_reviews(text,retailer):
    if not re.search(r'medicube\s+Zero\s+Pore\s+Pad',text,re.I):
        return None
    if retailer=='ulta':
        # Review Snapshot by PowerReviews: 3.9 195 Reviews.
        # Avoid picking unrelated counts or incentivized review body.
        m=re.search(r'\b([1-5](?:\.\d{1,2})?)\s+([\d,]{1,8})\s+Reviews\b',text,re.I)
    elif retailer=='target':
        # Dedicated item page: 4.4 out of 5 stars with 141 reviews.
        m=re.search(r'\b([1-5](?:\.\d{1,2})?)\s+out of 5 stars with\s+([\d,]{1,8})\s+reviews\b',text,re.I)
        if not m:
            m=re.search(r'\b([1-5](?:\.\d{1,2})?)\s+out of 5 stars\s+([\d,]{1,8})\s+star ratings\b',text,re.I)
    else:return None
    if not m:return None
    rating=float(m.group(1));count=int(m.group(2).replace(',',''))
    if rating<1 or rating>5 or count<1 or count>10_000_000:return None
    return {'rating':rating,'reviews_count':count}

def fetch_page(url):
    req=request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xhtml+xml'})
    with request.urlopen(req,timeout=14) as resp:
        if 'html' not in resp.headers.get('Content-Type','text/html').lower():
            raise ValueError('non-HTML response')
        return resp.read(900_000).decode('utf-8','replace')

def refresh(record=OUTPUT,fetcher=fetch_page,day=None):
    path=Path(record)
    try:data=json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):
        data={'retail':[],'retail_history':[]}
    day=day or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    history=list(data.get('product_review_history') or [])
    # Existing day/id observation is immutable unless source-corrected in
    # the same run: never fabricate history on prior dates.
    keyed={(x.get('date'),x.get('product_id')):x for x in history}
    states={}
    for product_id,spec in PAGES.items():
        try:
            visible=visible_text(fetcher(spec['url']))
            parsed=parse_product_reviews(visible,spec['retailer'])
            if not parsed:raise ValueError('product-specific visible aggregate counts missing')
            obs={
             'date':day,'country':'US','product_id':product_id,
             'retailer':spec['retailer'],'label':spec['name'],
             'source_url':spec['url'],'method':'official_individual_product_page',
             'verified':True,'scope':'온라인 상품 상세페이지의 누적 고객 리뷰·평점',
             'note':'실제 오프라인 매장별 판매량·매출, 리뷰 내용이 아님',
             **parsed
            }
            keyed[(day,product_id)]=obs
            states[product_id]='정상 관측'
        except Exception as ex:
            states[product_id]='공식 페이지 읽기 제한/검증 실패 · '+type(ex).__name__
    data['product_review_history']=sorted(keyed.values(),key=lambda x:(x.get('date',''),x.get('product_id','')))[-900:]
    data['product_review_sources']=[{**v} for v in PAGES.values()]
    data['product_review_status']={'checked_date':day,'source_results':states,
       'scope_note':'상품 상세페이지에 공개된 온라인 고객 리뷰·평점. 오프라인 POS 매출·출고량이나 재주문 증거 아님'}
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'review_sources':len(PAGES),'verified_today':sum(x=='정상 관측' for x in states.values()),
                      'history_entries':len(data['product_review_history'])},ensure_ascii=False))
    return data

if __name__=='__main__':
    refresh()
