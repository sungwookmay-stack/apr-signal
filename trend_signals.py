#!/usr/bin/env python3
"""Identify meaningful within-country, within-keyword Google Trends shifts.

Use one normalized interest-over-time SERIES per country/keyword. Weekly and
daily sampling receive different windows. Requires a material relative AND
absolute index movement and noise control. 0-100 Trends index is NOT demand,
sales or cross-country search volume; never compare absolute index levels
between countries or independently normalized query batches.
"""
from __future__ import annotations
import datetime as dt
import json
import statistics
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'data/demand.json'
OUTPUT=ROOT/'data/trend_signals.json'
MAX_STALE_DAYS=35

def _number(n):
    try:
        v=float(n)
        return v if 0<=v<=100 else None
    except (TypeError,ValueError):
        return None


def detect(trends, countries=None, today=None):
    today=today or dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date()
    names={x['code']:x['name'] for x in (countries or []) if isinstance(x,dict) and x.get('code')}
    series=defaultdict(lambda:defaultdict(dict))
    for x in trends or []:
        if not isinstance(x,dict) or x.get('partial'):
            continue
        cc,term=str(x.get('country') or '').strip(),str(x.get('term') or '').strip()
        date=str(x.get('date') or '')[:10]
        try: day=dt.date.fromisoformat(date)
        except ValueError:continue
        if not cc or not term or day>today or day<dt.date(2025,1,1):
            continue
        val=_number(x.get('index'))
        if val is None:continue
        # A single response's 0..100 series has one normalization denominator.
        # If historical API responses are combined, evaluate only the latest
        # complete dataset ID. CSV uploads have their own source ID.
        dataset=str(x.get('dataset') or x.get('source') or 'unknown')
        series[(cc,term)][dataset][day]=val
    results=[]
    for (cc,term),datasets in series.items():
        chosen=max(datasets, key=lambda key:(max(datasets[key]),len(datasets[key])))
        points=sorted(datasets[chosen].items())
        if len(points)<12 or (today-points[-1][0]).days>MAX_STALE_DAYS:
            continue
        gaps=[(points[i][0]-points[i-1][0]).days for i in range(1,len(points))]
        typical=statistics.median(gaps[-10:])
        if typical<=3:
            recent_n,base_n,granularity=7,28,'일간'
        elif typical<=12:
            recent_n,base_n,granularity=4,8,'주간'
        else:
            recent_n,base_n,granularity=2,6,'월간'
        baseline=points[-(recent_n+base_n):-recent_n]
        recent=points[-recent_n:]
        if len(baseline)<min(base_n,6) or len(recent)<recent_n:
            continue
        history=[y for _,y in baseline]
        recent_values=[y for _,y in recent]
        reference=statistics.mean(history)
        current=statistics.mean(recent_values)
        difference=current-reference
        change_pct=difference/reference*100 if reference>0 else None
        deviation=max(statistics.pstdev(history),4.0)
        z=difference/deviation
        # Avoid tiny-volume noise and index re-normalization overclaiming.
        if reference<10 or abs(difference)<8 or abs(z)<1.15:
            continue
        direction=None
        if change_pct is not None and change_pct>=35 and current>=15:
            direction='관심도 상승'
        if change_pct is not None and change_pct<=-30 and reference>=15:
            direction='관심도 하락'
        if direction is None:continue
        persistence=sum((v>reference if difference>0 else v<reference) for v in recent_values)
        if persistence < max(2,recent_n-1):
            continue
        results.append({
            'country':cc,'country_name':names.get(cc,cc),'keyword':term,
            'direction':direction,
            'delta_index':round(difference,1),
            'change_pct':round(change_pct,1),
            'recent_avg':round(current,1),'baseline_avg':round(reference,1),
            'baseline_points':len(baseline),'recent_points':len(recent),
            'granularity':granularity,'asof':points[-1][0].isoformat(),
            'dataset':chosen,
            'persistence':persistence,
            'strength':round(abs(difference)*min(abs(z),3),1),
            'explanation':('최근 '+str(recent_n)+'개 관측 평균 vs 직전 '+str(len(baseline))+
                           '개 평균. 동일 국가·키워드 내 0~100 상대 관심도. 판매량 아님.')
        })
    results.sort(key=lambda a:(-a['strength'],a['country'],a['keyword']))
    return {
        'updated_at':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'asof_date':today.isoformat(),
        'method':'trend-v1: weekly 4 vs 8 (daily 7 vs 28), absolute 8pt & relative +35%/-30% & >=1.15 baseline sigma, persistence and minimum level; same normalized series only',
        'source_note':'Google Trends 지수는 국가·키워드·기간별 0~100 상대관심도이며 국가 간 절대량을 비교하지 않습니다. 검색관심도 변화는 실제 매출·판매량·오프라인 POS가 아닙니다.',
        'alerts':results[:30],
        'evaluated_pairs':len(series),'detected_pairs':len(results)
    }


def update(trends_file=INPUT,output=OUTPUT):
    data=json.loads(Path(trends_file).read_text(encoding='utf-8'))
    report=detect(data.get('trends',[]),data.get('countries',[]))
    Path(output).parent.mkdir(parents=True,exist_ok=True)
    Path(output).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return report


if __name__=='__main__':
    result=update()
    print(json.dumps({k:result[k] for k in ('detected_pairs','evaluated_pairs','asof_date')},ensure_ascii=False))
