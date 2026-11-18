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
   if not group.startswith('서울특별시 '):raise DataError('regional_scope_mismatch')
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
 specs=[('country',c,c+'_3304',label) for c,label in [('US','한국→미국 · HS3304'),('JP','한국→일본 · HS3304'),('CN','한국→중국 · HS3304')]]
 specs += [('regional',region,id,label) for region,id,label in [('서울특별시 송파구','songpa_330499','송파구 제조지 · HS330499'),('서울특별시 금천구','geumcheon_330499','금천구 제조지 · HS330499')]]
 cache={}
 for kind,geo,id,label in specs:
  key=os.getenv('CUSTOMS_COUNTRY_API_KEY' if kind=='country' else 'CUSTOMS_REGIONAL_API_KEY','')
  previous=old.get(id,{});obs={r['month']:r for r in previous.get('observations',[])};errors=[];windows=[]
  for year in range(2022,int(end[:4])+1):
   start=f'{year}01';stop=min(f'{year}12',end)
   if start>stop:continue
   cache_key=(kind,geo if kind=='country' else '11',start,stop)
   if not key:errors.append({'window':[start,stop],'code':'missing_secret'});continue
   if cache_key not in cache:
    params={'strtYymm':start,'endYymm':stop}
    params.update({'hsSgn':'3304','cntyCd':geo} if kind=='country' else {'HsSgn':'330499','sidoCd':'11'})
    try:
     body=fetch(kind,key,params);cache[cache_key]=(parse_body(body,kind,geo,start,stop),None)
    except DataError as e:cache[cache_key]=({},str(e))
    except Exception:cache[cache_key]=({},'invalid_response')
    time.sleep(.2)
   records,error=cache[cache_key]
   if error:errors.append({'window':[start,stop],'code':error});continue
   windows.append([start,stop])
   # Absence never deletes last good history or becomes zero.
   for (g,m),value in records.items():
    if g==geo:obs[m]={'month':m,'value':value,'verified_at':now.isoformat()}
  unit='USD' if kind=='country' else 'native_unverified'
  status='missing_secret' if not key else 'partial' if errors and obs else 'api_error' if errors else 'success' if obs else 'no_data'
  item={'id':id,'label':label,'kind':kind,'hs_code':'3304' if kind=='country' else '330499','geography':geo,'source_url':SOURCES[kind], 'unit':unit,'unit_verified':kind=='country','status':status,'latest_month':max(obs) if obs else None,'observations':[obs[m] for m in sorted(obs)],'checked_at':now.isoformat(),'errors':errors,'verified_windows':windows,'geography_basis':'한국 수출 목적국' if kind=='country' else '수출신고 제조장소 우편번호','unit_note':'FOB 신고미화금액 달러' if kind=='country' else 'expUsdAmt 원시값: 공식 단위 검증 대기; 금액 그래프 비표시'}
  series.append(item)
 data={'schema_version':1,'checked_at':now.isoformat(),'requested_through_month':end[:4]+'-'+end[4:],'source_commit':os.getenv('GITHUB_SHA'),'series':series,'notes':['한국 지역/품목 통계이며 APR 수출·매출·재고가 아닙니다.','국가 HS3304와 지역 HS330499는 품목범위가 달라 직접 합산하지 않습니다.','지역은 제조장소 우편번호 기준이며 본사 소재지와 다를 수 있습니다.','매월15일경 전월까지 정정 반영. 수집 성공은 당월자료 발표를 뜻하지 않습니다.','누락은 0이 아니며 기존 확인값은 보존합니다. 과거 값은 공식 정정으로 변경될 수 있습니다.']}
 path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({'series':[{'id':s['id'],'status':s['status'],'rows':len(s['observations']),'latest_month':s['latest_month'],'errors':s['errors']} for s in series]},ensure_ascii=False))
if __name__=='__main__':main()
