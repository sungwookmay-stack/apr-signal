"""Point-in-time, evidence-first journal for the user's qualitative hypotheses.
No network/paid calls. A missing observation is never a bearish observation.
"""
import copy
import hashlib
import json
import math
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
KST = timezone(timedelta(hours=9))
METHOD = ('사진의 12개 정성 가설을 유지합니다. 수치 문턱이나 확률을 만들지 않습니다. '
          '한 시나리오의 4개 조건 모두 직접 입증되고 다른 시나리오가 동시에 충족되지 않을 때만 분류합니다. '
          '일부 수치·입점·검색·순위는 참고 근거이며 전체 가설 입증이 아닙니다. '
          '사진의 미래 기간은 목표 시점이지 이미 발생한 사실이 아닙니다. '
          '갱신일(KST)별 당시 자료를 저장하며 같은 날 변경은 수정 이력으로 보존합니다. 과거 날짜를 역산 생성하지 않습니다.')


def read(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return copy.deepcopy(default)


def moment(value):
    if not isinstance(value, str) or not value:
        return None
    try:
        value = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Date-only published dates are conservatively available at KST day end.
        if value.tzinfo is None:
            value = value.replace(tzinfo=KST)
        return value
    except ValueError:
        return None


def date_known(value, now):
    if not isinstance(value, str):
        return False
    parsed = moment(value)
    if parsed is None:
        return False
    if len(value) == 10:
        parsed += timedelta(days=1)
    return parsed <= now


def finite(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def official_url(url):
    try:
        host = urlparse(url).hostname or ''
        return url.startswith('https://') and any(host == d or host.endswith('.'+d) for d in
            ('dart.fss.or.kr', 'opendart.fss.or.kr', 'apr-in.com', 'aprd.io', 'ulta.com',
             'costco.com', 'walmart.com', 'boots.com', 'sgx.com', 'mas.gov.sg', 'hsa.gov.sg'))
    except (ValueError, AttributeError):
        return False


def financial_context(data, now):
    financials = read(data/'financials.json', {})
    filings = read(data/'dart_financials.json', {}).get('filings', [])
    # Only receipt number, never an invented report link; row period remains explicit.
    receipts = {f.get('period'): f.get('receipt_numbers', []) for f in filings}
    rows = [r for r in financials.get('quarterly', []) if
            date_known(r.get('available_from'), now) and date_known(r.get('asof'), now)]
    rows.sort(key=lambda r:r.get('asof',''))
    context = []
    for r in rows[-3:]:
        url = r.get('source_url')
        nums = receipts.get(r.get('period'), [])
        if nums:
            url = 'https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+str(nums[0])
        if not official_url(url):
            # Unverified/third-party links cannot become direct official proof.
            continue
        for key, label, unit in [('sales','연결 매출','억원'), ('op','연결 영업이익','억원'),
                                 ('ads_ratio_pct','광고선전비율','%'), ('shipping_ratio_pct','운반비율','%')]:
            if finite(r.get(key)):
                context.append(dict(id=r['period']+'_'+key,label=label,value=r[key],unit=unit,
                    period=r['period'],asof=r['asof'],available_from=r['available_from'],source=r.get('source',''),
                    source_url=url,evidence_type='reported' if key in ('sales','op') else 'derived',
                    note='연결 기준. 비용의 인과관계·채널 실수요 입증 아님. '+r.get('status','')))
        if finite(r.get('sales')) and r['sales']>0 and finite(r.get('op')):
            context.append(dict(id=r['period']+'_margin',label='연결 영업이익률',value=round(100*r['op']/r['sales'],2),unit='%',
                period=r['period'],asof=r['asof'],available_from=r['available_from'],source=r.get('source',''),
                source_url=url,evidence_type='derived',note='영업이익÷매출. FY2026 전체 마진이나 비용 원인 확정 아님.'))
    # Cumulative same-year released quarters; require every quarter 1..n and official sources.
    eligible = {r['period']:r for r in rows if any(c['period']==r['period'] for c in context)}
    if eligible:
        latest = max(eligible)
        year = latest[:4]
        selected = [eligible.get(year+'Q'+str(q)) for q in range(1,int(latest[-1])+1)] if latest[-1].isdigit() else []
        if selected and all(r and r.get('accounting_basis') and r.get('accounting_basis')==selected[0].get('accounting_basis') for r in selected) and all(r and finite(r.get('sales')) and finite(r.get('op')) for r in selected):
            for key,label in [('sales','공개 분기 누적 매출'),('op','공개 분기 누적 영업이익')]:
                context.append(dict(id='ytd_'+key,label=label,value=round(sum(r[key] for r in selected),2),unit='억원',
                    period=year+'Q1–'+latest,asof=selected[-1]['asof'],available_from=max(r['available_from'] for r in selected),
                    source='각 공개 분기 연결 실적 합계',source_url=next(c['source_url'] for c in context if c['period']==latest),
                    evidence_type='derived',note='연간 추정치 아님. 각 분기 원문·공개일은 개별 근거에 표시.'))
    return context


def evaluate(data_dir, now=None):
    data = Path(data_dir)
    now = now or datetime.now(timezone.utc)
    if isinstance(now,str):
        now = moment(now)
    if not isinstance(now,datetime):
        raise ValueError('now must be an ISO timestamp or datetime')
    if now.tzinfo is None:
        raise ValueError('now must include timezone')
    config = read(ROOT/'config/scenario_criteria.json', {})
    # Optional reviewed evidence ledger; raw news never qualifies automatically.
    ledger = read(data/'scenario_evidence.json', {}).get('evidence', [])
    scenarios = []
    for scenario in config.get('scenarios', []):
        output = {'id':scenario['id'],'label':scenario['label'],'conditions':[]}
        for criterion in scenario['conditions']:
            valid = [e for e in ledger if date_known(criterion.get('not_before'),now) and e.get('period_end','') >= criterion['not_before'] and e.get('condition_id')==criterion['id'] and
                e.get('review_status')=='verified' and e.get('evidence_type')=='direct' and
                e.get('covers_entire_condition') is True and e.get('stance') in ('supported','contradicted') and
                official_url(e.get('source_url')) and e.get('quote') and e.get('reason') and
                date_known(e.get('known_at'),now) and date_known(e.get('published_at'),now) and date_known(e.get('observed_at'),now) and
                date_known(e.get('period_end'),now)]
            stances={e['stance'] for e in valid}
            status = 'conflicting' if len(stances)>1 else next(iter(stances)) if stances else 'pending'
            condition={**criterion,'status':status,'reason': '가설 대상 기간 도래 전. 현재 공개자료는 참고 증거이며 미래 결과 확정 아님.' if not date_known(criterion.get('not_before'),now) else '공식 직접 근거 충돌, 판정 보류' if status=='conflicting' else
                '정성 가설 전체를 입증하는 직접 근거 미확보. 참고 지표만으로 확정하지 않음.' if not valid else
                ' / '.join(e['reason'] for e in valid),'evidence':copy.deepcopy(valid),
                'missing':[criterion['required']] if status in ('pending','conflicting') else []}
            output['conditions'].append(condition)
        scenarios.append(output)
    matched=[s['id'] for s in scenarios if all(c['status']=='supported' for c in s['conditions'])]
    classification=matched[0] if len(matched)==1 else 'pending'
    reason = ('모든 조건에 직접 근거가 있는 유일한 시나리오' if classification!='pending' else
              '가설 전체의 필수 근거 미확보 또는 충돌. 자료 부족은 Bear 또는 Base 판정이 아닙니다.')
    context=financial_context(data,now)
    context += [copy.deepcopy(c) for c in config.get('verified_context',[]) if date_known(c.get('known_at'),now) and date_known(c.get('available_from'),now) and date_known(c.get('asof'),now)]
    refs=read(data/'reference_signals.json',{})
    for r in refs.get('retail',[]):
        if r.get('retailer')=='ulta' and r.get('metric') in ('catalog_items','online_only_items') and date_known(r.get('date'),now) and official_url(r.get('source_url')) and finite(r.get('value')):
            context.append(dict(id='ulta_'+r['metric'],label=r.get('label'),value=r['value'],unit='개',period=r['date'],asof=r['date'],available_from=r['date'],source='Ulta 공식 상품 목록',source_url=r['source_url'],evidence_type='proxy',note='온라인 목록 관측. 판매량·매장수·재주문·채널 잠식 아님.'))
    # Explicit model assumption, not the source images' scoring system.
    partial = {c['id']: [] for s in scenarios for c in s['conditions']}
    # Static supplemental facts stay visible, but cannot be evergreen signals.
    latest_quarter=max((c['period'] for c in context if len(c.get('period',''))==6 and c['period'][4]=='Q' and c['period'][5] in '1234'),default='')
    for fact in context:
        asof=moment(fact.get('asof'))
        age=(now-asof).total_seconds()/86400 if asof else None
        superseded=bool(fact.get('partial_support') and len(fact.get('period',''))==6 and fact['period'][4]=='Q' and latest_quarter>fact['period'])
        stale=age is None or age>120
        fact['signal_eligible']=bool(fact.get('partial_support')) and not stale and not superseded
        fact['signal_exclusion_reason']='더 최신 분기 공개: 구분기 신호 집계 제외' if superseded else '자료 기준일 120일 초과 또는 기준일 없음: 신호 집계 제외' if stale else ''
        if not fact['signal_eligible']:
            continue
        for support in fact.get('partial_support', []):
            if support.get('condition_id') in partial:
                partial[support['condition_id']].append({'fact_id':fact['id'],'reason':support['reason']})
    counts=[]
    for scenario in scenarios:
        for condition in scenario['conditions']:
            condition['partial_evidence']=partial[condition['id']]
        counts.append({'id':scenario['id'],'label':scenario['label'],
            'partial_support':sum(bool(partial[c['id']]) for c in scenario['conditions']),
            'confirmed':sum(c['status']=='supported' for c in scenario['conditions']),
            'contradicted':sum(c['status']=='contradicted' for c in scenario['conditions']),
            'conflicting':sum(c['status']=='conflicting' for c in scenario['conditions']),
            'unknown':sum(c['status']=='pending' for c in scenario['conditions'])})
    ranked=sorted(counts,key=lambda c:c['partial_support'],reverse=True)
    leaning=ranked[0]['id'] if ranked and ranked[0]['partial_support']>=2 and ranked[0]['partial_support']>ranked[1]['partial_support'] and not ranked[0]['contradicted'] and not any(c['conflicting'] for c in counts) else None
    provisional={'status':'reference_signal' if leaning else 'pending','label':leaning.title()+' 쪽 참고 신호' if leaning else '참고 방향 보류',
        'counts':counts,'rule':'모델 가정: 현재 공식 관측의 부분지지 조건을 시나리오별로 중복 없이 셉니다. 최소 2개이며 유일 우세이고 직접 반증이 없을 때 참고 방향을 표시합니다. 미확인은 0점, 직접근거 충돌 시 보류. 기준일 120일 초과 또는 더 최신 분기가 공개된 구분기 근거는 집계 제외합니다. 120일은 명시적 모델 가정이며 확률·추천·미래 전체 판정이 아닙니다.',
        'limitation':'관측 가능한 부문에 편향될 수 있습니다. 2개 문턱은 사진 원문 기준이 아니며 문턱·집계 방법 변경에 민감합니다. 부분지지는 조건 전체 확인 수와 별개이며 미확인과 겹칩니다.'}
    snapshot={'date':now.astimezone(KST).date().isoformat(),'evaluated_at_utc':now.astimezone(timezone.utc).isoformat(),
        'classification':classification,'label':classification.title() if classification!='pending' else '판정 보류',
        'reason':reason,'provisional':provisional,'scenarios':scenarios,'context':context,'missing':sorted(set(m for s in scenarios for c in s['conditions'] for m in c['missing']))}
    content={k:v for k,v in snapshot.items() if k not in ('date','evaluated_at_utc')}
    snapshot['fingerprint']=hashlib.sha256(json.dumps(content,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    return snapshot


def update(data_dir, now=None):
    data=Path(data_dir)
    latest=evaluate(data,now)
    path=data/'scenario_monitor.json'
    old=read(path,{})
    history=copy.deepcopy(old.get('history',[]))
    if history and latest['date']<max(r['date'] for r in history):
        raise ValueError('historical backfill is not allowed')
    same=next((i for i,r in enumerate(history) if r.get('date')==latest['date']),None)
    if same is not None:
        prior=history[same]
        if moment(latest['evaluated_at_utc']) < moment(prior['evaluated_at_utc']):
            raise ValueError('cannot overwrite a later observation')
        revisions=prior.get('revisions',[])
        if prior.get('fingerprint') != latest['fingerprint']:
            revisions=revisions+[{k:v for k,v in prior.items() if k!='revisions'}]
        latest['revisions']=revisions
        history[same]=latest
    else:
        latest['revisions']=[]
        history.append(latest)
    result={'schema_version':1,'updated_at_utc':latest['evaluated_at_utc'],'methodology':METHOD,'latest':latest,'history':history}
    data.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    temp.replace(path)
    return result


if __name__=='__main__':
    update(ROOT/'data')
