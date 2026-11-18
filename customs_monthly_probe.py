"""Credential-safe official Customs probe. Never print URLs/errors containing keys."""
import os,json,urllib.request,urllib.parse,urllib.error,xml.etree.ElementTree as ET
SERVICES={
 'country':('CUSTOMS_COUNTRY_API_KEY','https://apis.data.go.kr/1220000/nitemtrade/getNitemtradeList',{'strtYymm':'202610','endYymm':'202610','hsSgn':'330499','cntyCd':'US'}),
 'regional':('CUSTOMS_REGIONAL_API_KEY','https://apis.data.go.kr/1220000/sigunguperprlstperacrs/getSigunguPerPrlstPerAcrs',{'strtYymm':'202610','endYymm':'202610','HsSgn':'330499','sidoCd':'11'})}
def main():
 results={}
 for name,(env,base,args) in SERVICES.items():
  key=os.getenv(env,'').strip()
  if not key:results[name]={'status':'missing_secret'};continue
  try:
   req=urllib.request.Request(base+'?'+urllib.parse.urlencode(dict(args,serviceKey=urllib.parse.unquote(key))))
   with urllib.request.urlopen(req,timeout=45) as r:body=r.read(4000000)
   root=ET.fromstring(body)
   code=root.findtext('.//resultCode') or root.findtext('.//returnReasonCode')
   items=root.findall('.//item')
   if code not in ('00','000','0000','0'):results[name]={'status':'api_error','code':code if code and code.isalnum() and len(code)<12 else 'unknown'};continue
   safe=[]
   allow={'year','statCd','statCdCntnKor1','hsCd','expDlr','expWgt','priodTitle','sggNm','hsSgn','korePrlstNm','expCnt','expUsdAmt'}
   for item in items:
    rec={c.tag:(c.text or '').strip() for c in item if c.tag in allow}
    if name=='country' or any(x in rec.get('sggNm','') for x in ('송파','금천')):safe.append(rec)
   results[name]={'status':'success','code':code,'item_count':len(items),'field_names':sorted({c.tag for item in items for c in item}),'selected_observations':safe}
  except urllib.error.HTTPError as e:results[name]={'status':'http_error','http_status':e.code}
  except Exception as e:results[name]={'status':'request_failed','error_type':type(e).__name__}
 print(json.dumps(results,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
