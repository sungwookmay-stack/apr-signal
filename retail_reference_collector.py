#!/usr/bin/env python3
"""Zero-key public retailer reference observations for APR SIGNAL.

Best-effort reads of *public* pages only. Never bypass access controls and
never interpret a catalog listing count or approximate purchase badge as
offline sell-through. On failure retain last confirmed observations.
"""
from __future__ import annotations
import datetime as dt
from html.parser import HTMLParser
from urllib import request
from pathlib import Path
import json
import re

ROOT=Path(__file__).resolve().parent
RECORD=ROOT/'data'/'reference_signals.json'
USER_AGENT='Mozilla/5.0 (compatible; APR-SIGNAL-Research/1.2; public market data)'
URLS={
 'ulta':'https://www.ulta.com/brand/medicube',
 'target':'https://www.target.com/c/facial-cleansers-skin-care-beauty/medicube/-/N-5xtziZq643leg6jg9',
 'amazon_weekly':'https://kbeautytmi.com/channels/amazon'
}

class VisibleText(HTMLParser):
 def __init__(self):
  super().__init__(convert_charrefs=True);self.skip=0;self.parts=[]
 def handle_starttag(self,tag,attrs):
  if tag in ('script','style','noscript','svg'):self.skip+=1
 def handle_endtag(self,tag):
  if tag in ('script','style','noscript','svg') and self.skip:self.skip-=1
 def handle_data(self,raw):
  if not self.skip and raw.strip():self.parts.append(raw.strip())

def text_of(html):
 x=VisibleText();x.feed(html)
 return re.sub(r'\s+',' ',' '.join(x.parts))

def public_fetch(url):
 req=request.Request(url,headers={'User-Agent':USER_AGENT,'Accept':'text/html,application/xhtml+xml'})
 with request.urlopen(req,timeout=12) as response:
  if 'html' not in response.headers.get('Content-Type','text/html').lower():
   raise ValueError('not HTML response')
  return response.read(1000000).decode('utf-8','replace')

def parse_ulta(text):
 if 'medicube' not in text.lower():return {}
 m=re.search(r'\b(\d{1,3})\s+results\b',text,re.I)
 if not m:return {}
 total=int(m.group(1))
 if total<1 or total>300:return {}
 values={'catalog_items':total}
 for key,pattern in (
   ('online_only_items',r'Online Only\s+(\d{1,3})\s+Products Available'),
   ('exclusive_items',r'Only at Ulta\s+(\d{1,3})\s+Products Available')):
  z=re.search(pattern,text,re.I)
  if z and 0<=int(z.group(1))<=total:values[key]=int(z.group(1))
 return values

def parse_target(text):
 if 'medicube' not in text.lower() or 'Zero Pore Pad' not in text:return {}
 out={}
 m=re.search(r'\b(\d{1,3})\s+results\b',text,re.I)
 if m and 1<=int(m.group(1))<=300:out['category_items']=int(m.group(1))
 # Badge must be close to the specific product, not another product's badge.
 m=re.search(r'\b(\d{1,4}(?:\.\d+)?)\s*([kKmM]?)\+\s*bought in last month.{0,210}?medicube Zero Pore Pad',text,re.I)
 if m:
  n=int(float(m.group(1))*{'k':1000,'m':1000000}.get(m.group(2).lower(),1))
  if 100<=n<=100000000:out['zero_pore_pad_bought_lower']=n
 return out

def parse_weekly(text):
 # Only source-defined full 100-rank coverage is eligible for a full count.
 if not re.search(r'US Beauty best sellers observed\s+100/100',text,re.I):
  return None
 m=re.search(r'\b(20\d\d)-W(\d\d)\s+snapshot\b',text,re.I)
 n=re.search(r'\bmedicube\s+medicube\s+best product\s*#\d+\s*[·•]\s*(\d+)\s+items overall\b',text,re.I)
 if not m or not n:return None
 week=f'{m.group(1)}-W{m.group(2)}'
 count=int(n.group(1))
 if not 0<=count<=100:return None
 return {'week':week,'count':count,'covered':100}

def today_kst():
 return dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()

def collect():
 if not RECORD.exists():return {'status':'no saved reference file'}
 try:existing=json.loads(RECORD.read_text(encoding='utf-8'))
 except (OSError,ValueError):return {'status':'invalid saved reference file'}
 today=today_kst()
 catalog={
  'catalog_items':('ulta','US','메디큐브 등록상품 수','Ulta 공식 브랜드 페이지 전체 결과 수'),
  'online_only_items':('ulta','US','온라인 전용 표시 상품','Ulta 브랜드 페이지 Online Only 필터'),
  'exclusive_items':('ulta','US','Only at Ulta 상품','Ulta 브랜드 페이지 독점 상품'),
  'category_items':('target','US','Target 세안 카테고리 내 상품','Target Face Washes 브랜드 필터(전체 상품 수 아님)'),
  'zero_pore_pad_bought_lower':('target','US','제로모공패드 최근 한 달 구매 표시','Target 상품의 반올림된 bought 배지(최소치)')
 }
 source={x['metric']:x for x in existing.get('retail',[])}
 success=[];failure=[]
 for place in ('ulta','target'):
  try:
   page=text_of(public_fetch(URLS[place]))
   found=parse_ulta(page) if place=='ulta' else parse_target(page)
   if not found:raise ValueError('expected branded visible fields not found')
   for metric,value in found.items():
    retailer,country,label,scope=catalog[metric]
    old=source.get(metric,{})
    source[metric]={
      **old,'date':today,'retailer':retailer,'country':country,'metric':metric,
      'value':value,'display':(str(value//1000)+'k+ bought' if metric=='zero_pore_pad_bought_lower' else str(value)+'개'),
      'label':label,'scope':scope,'source_url':URLS[place],
      'method':('official_bought_badge' if metric.endswith('_bought_lower') else 'official_catalog_page'),
      'note':('반올림된 온라인 구매 표기. 실제 매출·매장별 판매량과 다름' if metric.endswith('_bought_lower')
       else '판매 목록 / 필터에 표시된 상품 수. 전국 오프라인 입점 매장 수가 아님')
    }
   success.append(place+' '+','.join(found))
  except Exception as e:failure.append(place+': '+str(e)[:95])
 try:
  weekly=parse_weekly(text_of(public_fetch(URLS['amazon_weekly'])))
  if weekly is None:raise ValueError('full 100-rank weekly capture not verified')
  known={(x.get('week')) for x in existing.get('amazon_weekly',[])}
  if weekly['week'] not in known:
   existing.setdefault('amazon_weekly',[]).append({
    **weekly,'date':today,'country':'US','category':'Beauty & Personal Care',
    'source':'KBeautyTMI 제3자 주간 공개 자료 (100개 랭킹 표본)',
    'source_url':URLS['amazon_weekly'],'method':'independent_weekly_full_list',
    'note':'아마존 공식 데이터가 아니며 API.SH 부분 관측과 합산하지 않음'
   })
  success.append('independent US Beauty '+weekly['week'])
 except Exception as e:failure.append('weekly Top100: '+str(e)[:95])
 # Keep observations from other providers and older records, replacing only
 # the specific documented, successfully refreshed retailer metric.
 retained=[x for x in existing.get('retail',[]) if x.get('metric') not in source]
 existing['retail']=retained+list(source.values())
 existing.setdefault('collection',{})['last_attempt_utc']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
 existing['collection']['successes']=success
 existing['collection']['failures']=failure
 existing['collection']['notes']=[
  '공식 사이트 자동 접근이 제한되면 마지막 출처확인 값을 유지',
  '온라인 상품 수, 반올림된 구매 배지, 현지 검색은 매장별 POS 매출 자료가 아님',
  '제3자 미국 주간 Top100은 API.SH 부분 목록과 분리 관찰'
 ]
 existing['updated_at_utc']=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
 RECORD.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
 return {'status':'ok','successes':success,'failures':failure,
         'retail_metrics':len(existing['retail']),'external_weeks':len(existing.get('amazon_weekly',[]))}

if __name__=='__main__':
 print(json.dumps(collect(),ensure_ascii=False))
