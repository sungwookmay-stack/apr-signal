"""Disabled-by-default Decodo Top50 collector; never invoked on ordinary refreshes.

No production workflow calls this module until publication rights and integration are
resolved. This module intentionally does not merge Top50 into Top100 history.
"""
from __future__ import annotations
import datetime as dt
import json
import os
from pathlib import Path
import re
import subprocess
import urllib.error
import urllib.request
from urllib.parse import urlsplit

KST = dt.timezone(dt.timedelta(hours=9))
DAYS = {0, 2, 4, 5, 6}  # Mon Wed Fri Sat Sun, KST
MARKETS = {'US':'com','GB':'co.uk','DE':'de','FR':'fr','IT':'it','ES':'es',
           'CA':'ca','JP':'co.jp','AE':'ae','SA':'sa','EG':'eg','BR':'com.br'}
ENDPOINT = 'https://data.decodo.com/v1/scrape'
MONTHLY_ATTEMPT_CAP = 300  # 12 countries x at most 23 selected days = 276


def eligibility(env, now, morning_cron):
    """Fail closed. Delayed morning runs accepted only before KST noon.

    Only the existing 07:30 KST production morning cron is eligible.
    Public-use and free-plan gates require separate verification, not assumptions.
    """
    if morning_cron != '30 22 * * *':
        return 'morning_time_unconfigured'
    if env.get('DECODO_TOP50_ENABLED') != 'true':
        return 'disabled'
    if env.get('DECODO_PUBLIC_USE_AUTHORIZED') != 'true':
        return 'public_use_not_authorized'
    if env.get('DECODO_FREE_PLAN_CONFIRMED') != 'true':
        return 'free_plan_unconfirmed'
    if (env.get('GITHUB_EVENT_NAME') != 'schedule' or
            env.get('GITHUB_EVENT_SCHEDULE') != morning_cron):
        return 'not_morning_schedule'
    if env.get('GITHUB_RUN_ATTEMPT') != '1':
        return 'rerun_blocked'
    local = now.astimezone(KST)
    start = (7, 30)
    if local.weekday() not in DAYS:
        return 'excluded_kst_day'
    if not (start <= (local.hour, local.minute) < (12, 0)):
        return 'outside_morning_window'
    return None


def parsed_page(value, depth=0):
    if depth > 8:
        raise ValueError('response_shape')
    if isinstance(value, dict):
        if isinstance(value.get('results'), list) and 'page' in value:
            return value
        for key in ('results', 'content'):
            if key in value:
                try:
                    return parsed_page(value[key], depth+1)
                except ValueError:
                    pass
    elif isinstance(value, list) and len(value) == 1:
        return parsed_page(value[0], depth+1)
    elif isinstance(value, str):
        try:
            return parsed_page(json.loads(value), depth+1)
        except (TypeError, ValueError):
            pass
    raise ValueError('response_shape')


def inspect_top50(document, country, observed_at):
    page = parsed_page(document)
    url = urlsplit(str(page.get('url', '')))
    domain = MARKETS[country]
    if (url.hostname not in ('amazon.'+domain, 'www.amazon.'+domain) or
            'beauty' not in url.path.split('/') or str(page.get('page')) != '1'):
        raise ValueError('wrong_market_category_page')
    rows = page['results']
    normalized = []
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError('invalid_item')
        rank = item.get('pos')
        if isinstance(rank, bool) or not re.fullmatch(r'[0-9]+', str(rank)):
            raise ValueError('invalid_rank')
        asin, title = item.get('asin'), item.get('title')
        if (not isinstance(asin, str) or not re.fullmatch(r'[A-Z0-9]{10}', asin) or
                not isinstance(title, str) or not title.strip()):
            raise ValueError('missing_identity')
        normalized.append({'rank':int(rank), 'asin':asin, 'title':title.strip()[:500]})
    if (len(normalized) != 50 or {i['rank'] for i in normalized} != set(range(1,51)) or
            len({i['asin'] for i in normalized}) != 50):
        raise ValueError('incomplete_top50')
    return {'country':country, 'observed_at_utc':observed_at.isoformat(),
            'category':'beauty', 'limit':50, 'provider':'Decodo',
            'response_complete':True, 'amazon_live_crosschecked':False,
            'brand_verified':False, 'items':sorted(normalized,key=lambda i:i['rank'])}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_page(token, domain):
    # proxy_pool must be omitted: explicit premium caused HTTP400 in live trial.
    payload = {'target':'amazon_bestsellers','query':'beauty','domain':domain,
               'page_from':'1','parse':True}
    req = urllib.request.Request(ENDPOINT, data=json.dumps(payload).encode(),
          headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(req, timeout=120) as response:
        raw = response.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ValueError('oversize_response')
        return json.loads(raw)


def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)


def collect(state, env, now, morning_cron, persist, request=request_page):
    """Mutate isolated state; reserve each attempt before I/O; no retries.

    Failed current observations do not replace previous complete observations.
    Attempt counters are not a provider balance and never assert actual costs.
    """
    reason = eligibility(env, now, morning_cron)
    if reason:
        return {'status':'skipped','reason':reason,'attempts':0}
    token = env.get('DECODO_API_KEY','').strip()
    if (not token or any(c.isspace() for c in token) or
            token.lower().startswith(('bearer','curl'))):
        return {'status':'skipped','reason':'missing_or_malformed_key','attempts':0}
    local = now.astimezone(KST)
    day, month = local.date().isoformat(), local.strftime('%Y-%m')
    ledger = state.setdefault('attempts_by_month',{})
    daily = state.setdefault('attempts_by_day',{}).setdefault(day,[])
    observations = state.setdefault('latest_complete',{})
    checks = state.setdefault('latest_checks',{})
    made = 0
    pending=[(cc,domain) for cc,domain in MARKETS.items() if cc not in daily]
    capacity=max(0,MONTHLY_ATTEMPT_CAP-ledger.get(month,0))
    planned=pending[:capacity]
    if not planned and pending:
        return {'status':'paused','reason':'local_monthly_attempt_cap','attempts':0}
    # Reserve the entire batch before network I/O. If interrupted, unused
    # reservations remain consumed rather than risking duplicate billed calls.
    if planned:
        daily.extend(cc for cc,_ in planned)
        ledger[month]=ledger.get(month,0)+len(planned)
        for cc,_ in planned:
            checks[cc]={'checked_at_utc':now.isoformat(),'status':'attempt_reserved'}
        persist(state)
    for country, domain in planned:
        made += 1
        try:
            result = request(token, domain)
            snapshot = inspect_top50(result,country,now)
            observations[country] = snapshot
            checks[country] = {'checked_at_utc':now.isoformat(),'status':'complete_50'}
        except urllib.error.HTTPError as exc:
            # Do not reveal response bodies, headers, tokens or request URLs.
            checks[country] = {'checked_at_utc':now.isoformat(), 'status':'http_error',
                               'http_status':exc.code}
            persist(state)
            return {'status':'paused','reason':'provider_http_error','attempts':made}
        except (OSError, ValueError, TypeError, TimeoutError):
            checks[country] = {'checked_at_utc':now.isoformat(),'status':'invalid_or_unavailable'}
        persist(state)
    if len(planned)<len(pending):
        return {'status':'paused','reason':'local_monthly_attempt_cap','attempts':made}
    return {'status':'finished','attempts':made}


BRANDS = {
    'medicube': ('메디큐브', r'(?<![a-z])medicube(?![a-z])|메디큐브|メディキューブ'),
    'aprilskin': ('에이프릴스킨', r'(?<![a-z])april\s*skin(?![a-z])|에이프릴\s*스킨|エイプリルスキン'),
    'forment': ('포맨트', r'(?<![a-z])forment(?![a-z])|포맨트'),
    'glamd': ('글램디 바이오', r'(?<![a-z])glam[.\s]*d(?:\s+bio)?(?![a-z])|글램디'),
    # Short NDY and generic English "nerdy" need more evidence; do not match them.
    'ndy': ('NDY', r'널디'),
    'photogray': ('포토그레이', r'(?<![a-z])photogray(?![a-z])|포토그레이'),
}
BRAND_SOURCE = 'https://www.apr-in.com/en/apr_about.html'


def candidate_brands(title):
    return [key for key,(_,pattern) in BRANDS.items() if re.search(pattern,title,re.I)]


def display_snapshot(current, previous=None, verified_asins=None):
    """Separate APR brands. Exact title mentions remain candidates, not proof.

    Ambiguous multi-brand titles are withheld from single-brand counts.
    verified_asins is a reviewed country-specific {asin:brand_id} mapping.
    Legacy sets apply only to medicube for backwards-compatible test fixtures.
    """
    verified_asins = verified_asins or {}
    if isinstance(verified_asins,set): verified_asins={asin:'medicube' for asin in verified_asins}
    comparable = bool(previous and previous.get('country') == current['country']
                      and previous.get('category') == current['category']
                      and previous.get('response_complete'))
    old = {x['asin']:x for x in previous['items']} if comparable else {}
    groups={brand:{'label':label,'verified_count':0,'candidate_count':0,'items':[],'exited':[]}
            for brand,(label,_) in BRANDS.items()}
    ambiguous=[]
    def identity(item):
        confirmed=verified_asins.get(item['asin'])
        if confirmed in BRANDS: return confirmed,'verified'
        matches=candidate_brands(item['title'])
        return (matches[0],'title_candidate') if len(matches)==1 else (None,None)
    for item in current['items']:
        brand,status=identity(item)
        if not brand:
            if len(candidate_brands(item['title']))>1: ambiguous.append(item)
            continue
        earlier=old.get(item['asin'])
        row={**item,'brand_id':brand,'brand_status':status,
             'previous_rank':earlier['rank'] if earlier else None,
             'rank_change':earlier['rank']-item['rank'] if earlier else None,
             'movement':'ranked' if earlier else ('entered_top50' if comparable else 'first_observation')}
        groups[brand]['items'].append(row)
        groups[brand]['verified_count' if status=='verified' else 'candidate_count']+=1
    current_asins={x['asin'] for x in current['items']}
    if comparable:
        for item in previous['items']:
            brand,status=identity(item)
            if brand and item['asin'] not in current_asins:
                groups[brand]['exited'].append({**item,'brand_id':brand,'brand_status':status,
                                               'movement':'not_in_current_top50','current_rank':None})
    return {'country':current['country'],'category':'beauty','limit':50,
            'observed_at_utc':current['observed_at_utc'],
            'previous_observed_at_utc':previous['observed_at_utc'] if comparable else None,
            'response_complete':True,'amazon_live_crosschecked':current.get('amazon_live_crosschecked',False),
            'brand_source':BRAND_SOURCE,'brands':groups,'ambiguous_items':ambiguous,
            **groups['medicube']}


def main():
    root=Path(__file__).resolve().parent
    state_path=root/'state'/'decodo_top50.json'
    try:
        state=json.loads(state_path.read_text())
    except FileNotFoundError:
        state={}
    # Corrupt state is deliberately fatal: never reset an unknown budget ledger.
    now=dt.datetime.now(dt.timezone.utc)
    before=dict(state.get('latest_complete',{}))
    reserved=False
    def persist(value):
        nonlocal reserved
        save(state_path,value)
        if not reserved and os.environ.get('GITHUB_ACTIONS')=='true':
            # Fail before API I/O if durable reservation cannot be pushed.
            for args in (
                ['git','config','user.name','github-actions[bot]'],
                ['git','config','user.email','41898282+github-actions[bot]@users.noreply.github.com'],
                ['git','add','state/decodo_top50.json'],
                ['git','commit','-m','data: reserve Decodo morning batch [skip ci]'],
                ['git','push']):
                subprocess.run(args,cwd=root,check=True,capture_output=True)
        reserved=True
    result=collect(state,os.environ,now,'30 22 * * *',persist)
    public_path=root/'data'/'top50.json'
    try:
        public=json.loads(public_path.read_text())
    except FileNotFoundError:
        public={'snapshots':[]}
    for cc,current in state.get('latest_complete',{}).items():
        if current.get('observed_at_utc')==before.get(cc,{}).get('observed_at_utc'): continue
        public.setdefault('snapshots',[]).append(display_snapshot(current,before.get(cc)))
    public.update(status=result.get('reason',result['status']),limit=50,
                  schedule='월·수·금·토·일 07:30 KST',latest_checks=state.get('latest_checks',{}))
    save(public_path,public)
    print(json.dumps(result))  # fixed status + request counts only, never secrets


if __name__ == '__main__':
    main()
