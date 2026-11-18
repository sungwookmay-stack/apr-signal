"""Read-only KCS boundary probe. No credentials, URLs or raw exceptions emitted."""
import json,os,datetime as dt
from xml.etree import ElementTree as ET
from customs_monthly import fetch,amount,month

def main():
 key=os.getenv('CUSTOMS_REGIONAL_API_KEY','')
 result={'source':'https://www.data.go.kr/data/15134343/openapi.do','hs_code':'330499','sido_candidate':'41','unit_verified':False,'aggregation_enabled':False,'windows':[]}
 if not key:result['status']='missing_secret'
 else:
  for year in range(2022,2027):
   start=f'{year}01';end=f'{year}12' if year<2026 else '202610'
   out={'start':start,'end':end}
   try:
    root=ET.fromstring(fetch('regional',key,{'strtYymm':start,'endYymm':end,'HsSgn':'330499','sidoCd':'41'}))
    code=root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
    if code not in ('00','0','000','0000'):raise ValueError('api_error')
    rows=[];seen=set();names=set()
    for e in root.findall('.//item'):
     r={c.tag:(c.text or '').strip() for c in e};name=r.get('sggNm','');names.add(name)
     if not name.startswith('경기도 '):raise ValueError('scope_mismatch')
     if not any(x in name for x in ('화성','만세구','효행구','병점구','동탄구')):continue
     m=month(r.get('priodTitle'));hs=r.get('hsSgn')
     if hs!='330499' or not start<=m.replace('-','')<=end:raise ValueError('scope_mismatch')
     identity=(m,name)
     if identity in seen:raise ValueError('duplicate_row')
     seen.add(identity);rows.append({'month':m,'geography':name,'raw_value':amount(r.get('expUsdAmt')),'export_count':r.get('expCnt')})
    out.update(status='success',all_geography_names=sorted(names),observations=rows)
   except Exception as e:out.update(status='failed',error_type=type(e).__name__)
   result['windows'].append(out)
 print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
