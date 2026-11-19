"""Apply verified KBTY issuer snapshot and saved DART files without providers."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from build_data import collect_kbty
from financial_engine import update
from update_data import write_atomic

def main():
    data=ROOT/'data'
    kbty=collect_kbty(offline_snapshot=True)
    financials=update()
    quarter=next((r for r in financials['quarterly'] if r['period']=='2026Q3'), {})
    assert kbty.get('trading_confirmed') and kbty.get('apr_holding_as_of','')>='2026-11-18'
    assert quarter.get('source_url','').endswith('20261113001366')
    p=data/'status.json'
    status=json.loads(p.read_text(encoding='utf-8'))
    status['kbty_status']=kbty['status']
    write_atomic(p,json.dumps(status,ensure_ascii=False,indent=2)+'\n')
    p=data/'bootstrap.js'
    prefix='window.APR_BOOTSTRAP = '
    source=p.read_text(encoding='utf-8')
    assert source.startswith(prefix)
    doc=json.loads(source[len(prefix):].strip().removesuffix(';'))
    doc.update(kbty=kbty, financials=financials, status=status)
    write_atomic(p,prefix+json.dumps(doc,ensure_ascii=False,separators=(',',':'))+';\n')
    print('KBTY: trading confirmed, APR holdings as of',kbty['apr_holding_as_of'])
    print('APR Q3: verified DART consolidated quarterly filing from',quarter['available_from'])

if __name__=='__main__':
    main()
