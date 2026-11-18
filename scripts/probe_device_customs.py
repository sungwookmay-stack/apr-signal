"""Read-only official Customs code probe. No credentials/URLs/raw errors logged.
Never writes dashboard data. National industry values are not APR exports.
"""
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from xml.etree import ElementTree as ET

HS = '8543702020'
BASE = 'https://apis.data.go.kr/1220000/'

def probe(kind, start, end):
    key = os.environ.get('CUSTOMS_COUNTRY_API_KEY', '').strip()
    result = {'kind': kind, 'hs': HS, 'start': start, 'end': end}
    if not key:
        return dict(result, status='missing_secret')
    params = {'serviceKey': urllib.parse.unquote(key), 'strtYymm': start, 'endYymm': end, 'hsSgn': HS}
    endpoint = 'Itemtrade/getItemtradeList'
    if kind == 'US':
        endpoint = 'nitemtrade/getNitemtradeList'
        params['cntyCd'] = 'US'
    try:
        with urllib.request.urlopen(BASE + endpoint + '?' + urllib.parse.urlencode(params), timeout=40) as r:
            root = ET.fromstring(r.read(2000000))
        code = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode') or ''
        if code not in ('00', '0', '000', '0000'):
            return dict(result, status='api_error', code=code if re.fullmatch(r'[0-9A-Za-z]{1,10}', code) else 'unknown')
        rows = []
        for e in root.findall('.//item'):
            year = e.findtext('year') or ''
            if year in ('총계', '합계'):
                continue
            hs = e.findtext('hsCd') or ''
            if hs != HS or not re.fullmatch(r'20\d{2}[.-](0[1-9]|1[0-2])', year):
                return dict(result, status='scope_mismatch')
            if kind == 'US' and e.findtext('statCd') != 'US':
                return dict(result, status='country_mismatch')
            value = (e.findtext('expDlr') or '').replace(',', '')
            if not value.isdigit():
                return dict(result, status='amount_invalid')
            # Only documented public trade fields; never raw body/request/errors.
            name = e.findtext('statKor') or ''
            if len(name) > 100 or any(c in name for c in '<>&'):
                return dict(result, status='name_invalid')
            rows.append({'month': year, 'hs': hs, 'name': name, 'exports_usd': int(value)})
        return dict(result, status='ok' if rows else 'no_rows', observations=rows)
    except urllib.error.HTTPError as e:
        return dict(result, status='http_error', code=e.code)
    except Exception:
        return dict(result, status='transport_or_parse_error')

if __name__ == '__main__':
    today = dt.datetime.now(dt.timezone.utc).date()
    latest = (today.replace(day=1)-dt.timedelta(days=1)).strftime('%Y%m')
    for kind, start, end in [('US', latest, latest), ('national', '202404', '202407'), ('national', latest, latest)]:
        print(json.dumps(probe(kind, start, end), ensure_ascii=False))
