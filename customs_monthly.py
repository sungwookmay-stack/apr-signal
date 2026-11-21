"""Monthly official Customs observations; no credentials or request URLs in output.
Country HS3304 includes returned HSK10 children, excluding grand totals.
Regional HS330499 is manufacturing-postcode based, NOT headquarters or APR sales.
"""
import datetime as dt,json,os,re,time,urllib.request,urllib.parse,urllib.error
from pathlib import Path
from xml.etree import ElementTree as ET
COUNTRY='https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList'
REGIONAL='https://apis.data.go.kr/1220000/sigunguperprlstperacrs/getSigunguPerPrlstPerAcrs'
SOURCES={'country':'https://www.data.go.kr/data/15100475/openapi.do','regional':'https://www.data.go.kr/data/15134343/openapi.do'}
class DataError(Exception):pass
REGIONAL_SIDO={'서울특별시 송파구':'11','서울특별시 금천구':'11','경기도 화성시':'41','경기도 평택시':'41','전북특별자치도 완주군':'52'}
REGIONAL_PREFIX={'11':'서울특별시 ', '41':'경기도 ', '52':'전북특별자치도 '}
# Use contemporary administrative code only; do not splice legacy code 45 history.
REGIONAL_EXPANSION=[
 ('경기도 평택시','pyeongtaek_330499','평택시 제조지 · HS330499 (지역 참고)',2022),
 ('전북특별자치도 완주군','wanju_330499','완주군 제조지 · HS330499 (지역 참고)',2024),
]
EXPANSION_START={ident:year for _,ident,_,year in REGIONAL_EXPANSION}

def relative_comparable(obs, errors, windows, first_year, through):
 required_months={f'{year}-{month:02}' for year in range(first_year,int(through[:4])+1)
                  for month in range(1,13) if f'{year}{month:02}'<=through}
 required_windows={(f'{year}01',min(f'{year}12',through)) for year in range(first_year,int(through[:4])+1)}
 return bool(required_months) and not errors and set(obs)==required_months and required_windows=={tuple(window) for window in windows}

# KCS cntyCd uses these two-letter destination codes (GB, not UK).
# Keep China's historical reference series alongside all configured demand markets.
KCS_COUNTRY_CODES = {'US','GB','DE','FR','IT','ES','CA','JP','AE','SA','EG','QA','KW','BR','AR','CL','CN'}
def country_specs(config):
 specs=[];seen=set()
 for market in list(config.get('markets',[]))+[{'code':'CN','name':'중국'}]:
  code=market.get('code','')
  if code in seen:continue
  if code not in KCS_COUNTRY_CODES:raise DataError('unsupported_country_code')
  seen.add(code)
  specs.append(('country',code,code+'_3304','한국→'+market.get('name',code)+' · HS3304'))
 return specs

def amount(v):
 s=str(v or '').replace(',','').strip()
 if not re.fullmatch(r'\d+',s):raise DataError('invalid_amount')
 return int(s)
def month(v):
 s=str(v).strip().replace('.','-')
 if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])',s):raise DataError('invalid_month')
 return s

def parse_body(body,kind,code,start,end):
 root=ET.fromstring(body)
 result=root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
 if result not in ('00','0','000','0000'):raise DataError('api_'+str(result) if str(result).isalnum() and len(str(result))<12 else 'api_error')
 rows=root.findall('.//item');seen=set();out={};grand=None;sumdetail=0
 for e in rows:
  r={c.tag:(c.text or '').strip() for c in e}
  if kind=='country' and r.get('year') in ('총계','합계'):
   if grand is not None:raise DataError('duplicate_total')
   grand=amount(r.get('expDlr'));continue
  m=month(r.get('year') if kind=='country' else r.get('priodTitle'))
  if not start<=m.replace('-','')<=end:raise DataError('out_of_window')
  hs=r.get('hsCd','') if kind=='country' else r.get('hsSgn','')
  if kind=='country':
   if not hs.startswith('3304') or len(hs) not in (4,6,10) or r.get('statCd')!=code:raise DataError('scope_mismatch')
   val=amount(r.get('expDlr'));group=code
  else:
   if hs!='330499':raise DataError('scope_mismatch')
   val=amount(r.get('expUsdAmt'));group=r.get('sggNm','')
   prefix=REGIONAL_PREFIX.get(REGIONAL_SIDO.get(code))
   if not prefix or not group.startswith(prefix):raise DataError('regional_scope_mismatch')
   # Never silently join a city series to new districts or double-count parent/children.
   if code=='경기도 화성시' and (group.startswith('경기도 화성시 ') or any(x in group for x in ('만세구','효행구','병점구','동탄구'))):raise DataError('regional_boundary_changed')
   if code=='경기도 평택시' and group.startswith('경기도 평택시 '):raise DataError('regional_boundary_changed')
   if group!=code:continue
  identity=(m,hs,group)
  if identity in seen:raise DataError('duplicate_row')
  if kind=='country' and any(mm==m and gg==group and (hh.startswith(hs) or hs.startswith(hh)) for mm,hh,gg in seen):raise DataError('overlapping_hs_scope')
  seen.add(identity);sumdetail+=val
  out[(group,m)]=out.get((group,m),0)+val
 if kind=='country' and grand is not None and grand!=sumdetail:raise DataError('total_mismatch')
 return out

def fetch(kind,key,params):
 base=COUNTRY if kind=='country' else REGIONAL
 query=dict(params,serviceKey=urllib.parse.unquote(key.strip()))
 try:
  with urllib.request.urlopen(base+'?'+urllib.parse.urlencode(query),timeout=45) as response:body=response.read(8000000)
  return body
 except urllib.error.HTTPError as e:raise DataError('http_'+str(e.code)) from None
 except Exception:raise DataError('transport_error') from None

def main():
 now=dt.datetime.now(dt.timezone.utc);today=(now+dt.timedelta(hours=9)).date();end=(today.replace(day=1)-dt.timedelta(days=1)).strftime('%Y%m')
 path=Path('data/customs_monthly.json');prior=json.loads(path.read_text()) if path.exists() else {}
 old={s['id']:s for s in prior.get('series',[])};series=[]
 specs=country_specs(json.loads(Path('config/markets.json').read_text()))
 specs += [('regional',region,id,label) for region,id,label in [('서울특별시 송파구','songpa_330499','송파구 제조지 · HS330499'),('서울특별시 금천구','geumcheon_330499','금천구 제조지 · HS330499'),('경기도 화성시','hwaseong_330499','화성시 제조지 · HS330499')]]
 specs += [('regional',geo,ident,label) for geo,ident,label,_ in REGIONAL_EXPANSION]
 expansion_only=os.getenv('CUSTOMS_REGIONAL_EXPANSION_ONLY')=='true'
 if expansion_only:
  specs=[spec for spec in specs if spec[2] in EXPANSION_START]
  series=[item for item in prior.get('series',[]) if item.get('id') not in EXPANSION_START]
 cache={}
 retry_only=os.getenv('CUSTOMS_RETRY_FAILED')=='true'
 for kind,geo,id,label in specs:
  key=os.getenv('CUSTOMS_COUNTRY_API_KEY' if kind=='country' else 'CUSTOMS_REGIONAL_API_KEY','')
  previous=old.get(id,{});obs={r['month']:r for r in previous.get('observations',[])};errors=[];windows=[]
  failed={tuple(e['window']) for e in previous.get('errors',[]) if 'window' in e}
  if retry_only and previous and not failed:
   if id in EXPANSION_START and previous.get('latest_month','')!=end[:4]+'-'+end[4:]:
    previous=dict(previous,relative_comparable=False,relative_basis='incomplete_or_unverified_monthly_scope')
   series.append(previous);continue
  if retry_only:windows=[w for w in previous.get('verified_windows',[]) if tuple(w) not in failed]
  for year in range(EXPANSION_START.get(id,2022),int(end[:4])+1):
   start=f'{year}01';stop=min(f'{year}12',end)
   if start>stop:continue
   if retry_only and previous and (start,stop) not in failed:continue
   cache_key=(kind,geo if kind=='country' else REGIONAL_SIDO[geo],start,stop)
   if not key:errors.append({'window':[start,stop],'code':'missing_secret'});continue
   if cache_key not in cache:
    params={'strtYymm':start,'endYymm':stop}
    params.update({'hsSgn':'3304','cntyCd':geo} if kind=='country' else {'HsSgn':'330499','sidoCd':REGIONAL_SIDO[geo]})
    try:
     body=fetch(kind,key,params);cache[cache_key]=(body,None)
    except DataError as e:cache[cache_key]=({},str(e))
    except Exception:cache[cache_key]=({},'invalid_response')
    time.sleep(.2)
   body,error=cache[cache_key]
   if error:errors.append({'window':[start,stop],'code':error});continue
   try:records=parse_body(body,kind,geo,start,stop)
   except DataError as e:errors.append({'window':[start,stop],'code':str(e)});continue
   except Exception:errors.append({'window':[start,stop],'code':'invalid_response'});continue
   if id in EXPANSION_START:
    expected={f'{start[:4]}-{month:02}' for month in range(int(start[4:]),int(stop[4:])+1)}
    if {m for _,m in records}!=expected:errors.append({'window':[start,stop],'code':'regional_incomplete_window'})
   if kind=='regional' and not records:
    errors.append({'window':[start,stop],'code':'regional_no_matching_rows'});continue
   if not errors or errors[-1]['window']!=[start,stop]:windows.append([start,stop])
   # Absence never deletes last good history or becomes zero.
   for (g,m),value in records.items():
    if g==geo:obs[m]={'month':m,'value':value,'verified_at':now.isoformat()}
  unit='USD' if kind=='country' else 'native_unverified'
  status='missing_secret' if not key else 'partial' if errors and obs else 'api_error' if errors else 'success' if obs else 'no_data'
  item={'id':id,'label':label,'kind':kind,'hs_code':'3304' if kind=='country' else '330499','geography':geo,'source_url':SOURCES[kind], 'unit':unit,'unit_verified':kind=='country','status':status,'latest_month':max(obs) if obs else None,'observations':[obs[m] for m in sorted(obs)],'checked_at':now.isoformat(),'errors':errors,'verified_windows':windows,'geography_basis':'한국 수출 목적국' if kind=='country' else '수출신고 제조장소 우편번호','unit_note':'FOB 신고미화금액 달러' if kind=='country' else 'expUsdAmt 원시값: 공식 단위 검증 대기; 금액 그래프 비표시'}
  if id in EXPANSION_START:
   item['relative_comparable']=relative_comparable(obs,errors,windows,EXPANSION_START[id],end)
   item['relative_basis']='exact_scope_complete_monthly' if item['relative_comparable'] else 'incomplete_or_unverified_monthly_scope'
   item['regional_sido_code']=REGIONAL_SIDO[geo]
   item['expected_start_month']=f'{EXPANSION_START[id]}-01'
   item['scope_note']='해당 지역 화장품 업종 참고 지표; APR·PN/PDRN의 품목별 수출 또는 제조 증거가 아닙니다.'
  series.append(item)
 if not expansion_only:
  from device_customs_monthly import collect_device_series
  series.extend(collect_device_series(json.loads(Path('config/markets.json').read_text()),prior.get('series',[]),os.getenv('CUSTOMS_COUNTRY_API_KEY',''),now,end,retry_only=retry_only))
 data={'schema_version':1,'checked_at':now.isoformat(),'requested_through_month':end[:4]+'-'+end[4:],'source_commit':os.getenv('GITHUB_SHA'),'series':series,'notes':['한국 지역/품목 통계이며 APR 수출·매출·재고가 아닙니다.','국가 HS3304와 지역 HS330499는 품목범위가 달라 직접 합산하지 않습니다.','지역은 제조장소 우편번호 기준이며 본사 소재지와 다를 수 있습니다.','매월15일경 전월까지 정정 반영. 수집 성공은 당월자료 발표를 뜻하지 않습니다.','누락은 0이 아니며 기존 확인값은 보존합니다. 과거 값은 공식 정정으로 변경될 수 있습니다.']}
 path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'series':[{'id':s['id'],'status':s.get('status'),'rows':len(s.get('observations',[])),'latest_month':s.get('latest_month'),'errors':s.get('errors',[])} for s in series]},ensure_ascii=False))
if __name__=='__main__':main()
