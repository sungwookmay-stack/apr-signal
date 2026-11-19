import copy, json
import sys
from pathlib import Path
from update_data import fetch_fx_ecb_zip, pack, write_atomic

root=Path(sys.argv[1])
load=lambda name:json.loads((root/(name+'.json')).read_text())
market=load('market'); status=load('status'); raw=copy.deepcopy(market)
both=fetch_fx_ecb_zip()
fx_sources=market['meta']['fx_sources']
prev_usd=market['meta']['usd_fx_last']; prev_eur=market['meta']['eur_fx_last']
assert all('ECB official' in fx_sources[b] for b in ('USD','EUR'))
if min(max(both['USD']),max(both['EUR']))<=max(prev_usd,prev_eur):
    sys.exit('No newer official FX.')
for b,field in (('USD','usdkrw'),('EUR','eurkrw')):
    old={r['date']:r[field] for r in raw['fx'] if r.get(field) is not None}
    old.update({d:v for d,v in both[b].items() if d>max(old)})
    both[b]=old
rebuilt=pack(market['series'],market['meta']['stock_source'],both,fx_sources,[],{},market['logistics'])
for k in ('usd_fx_last','eur_fx_last'):
    market['meta'][k]=rebuilt['meta'][k]
market['series']=rebuilt['series'];market['fx']=rebuilt['fx']
protected=lambda rows:[{k:v for k,v in x.items() if k not in {'usdkrw','eurkrw','fx_usd_date','fx_eur_date','close_usd'}} for x in rows]
assert protected(market['series'])==protected(raw['series']) and market['logistics']==raw['logistics']
assert market['fx'][:len(raw['fx'])]==raw['fx']
status['fx_last']=market['meta']['usd_fx_last']
write_atomic(root/'market.json',json.dumps(market,ensure_ascii=False,separators=(',',':'))+'\n');write_atomic(root/'status.json',json.dumps(status,ensure_ascii=False,indent=2)+'\n')
p=root/'bootstrap.js';prefix='window.APR_BOOTSTRAP = '
txt=p.read_text();assert txt.startswith(prefix)
doc=json.loads(txt[len(prefix):].strip().removesuffix(';'))
doc.update(market=market,status=status)
p.write_text(prefix+json.dumps(doc,separators=(',',':'),ensure_ascii=False)+';\n',encoding='utf-8')
print(prev_usd,'->',market['meta']['usd_fx_last'],market['fx'][-3:])
