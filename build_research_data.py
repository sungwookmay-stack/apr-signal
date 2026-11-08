#!/usr/bin/env python3
"""Produce static APR financial/valuation and Trends significance snapshots.

Zero paid API calls. The financial inputs are verified company filings stored
under config/. Trends reuse existing data/demand.json. This is safe on routine
builds (morning, afternoon or code-only pushes), and updates bootstrap.js so
the dashboard can fall back to the last saved snapshots if fetch is offline.
"""
from __future__ import annotations

import json
from pathlib import Path

import financial_engine
import trend_signals

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'


def read(path,default):
    try:return json.loads(path.read_text(encoding='utf-8'))
    except (OSError,ValueError):return default


def build():
    financial=financial_engine.update()
    try:
        trends=trend_signals.update()
    except (OSError,ValueError,TypeError) as exc:
        trends=read(DATA/'trend_signals.json',{
          'evaluated_pairs':0,'detected_pairs':0,'alerts':[],
          'status':'Google Trends 공개데이터 분석 실패',
          'source_note':'기존 공개 관측치가 없어 신호 미판정'
        })
        trends['status']='기존 Google Trends 기록 유지 · 최신 분석 실패'
        trends['error_type']=type(exc).__name__
        (DATA/'trend_signals.json').write_text(
            json.dumps(trends,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    bootstrap=DATA/'bootstrap.js'
    try:
        js=bootstrap.read_text(encoding='utf-8')
        prefix='window.APR_BOOTSTRAP = '
        snapshot=json.loads(js[len(prefix):].rstrip(';\n')) if js.startswith(prefix) else {}
        if not isinstance(snapshot,dict):snapshot={}
    except (OSError,ValueError):
        snapshot={}
    # Keep the static bootstrap fallback synchronized with explicitly
    # refreshed market/technical files after the free historical backfill.
    snapshot['market']=read(DATA/'market.json', snapshot.get('market', {}))
    snapshot['technical']=read(DATA/'technical.json', snapshot.get('technical', {}))
    snapshot['financials']=financial
    snapshot['trend_signals']=trends
    snapshot['apr_theses']=read(DATA/'apr_theses.json',{})
    snapshot['reference_signals']=read(DATA/'reference_signals.json',{})
    snapshot['dart_ownership']=read(DATA/'dart_ownership.json',{})
    snapshot['dart_financials']=read(DATA/'dart_financials.json',{})
    snapshot['dart_capital']=read(DATA/'dart_capital.json',{})
    bootstrap.write_text('window.APR_BOOTSTRAP = '+
        json.dumps(snapshot,ensure_ascii=False,separators=(',',':'))+';\n',
        encoding='utf-8')
    print(json.dumps({
        'financial_periods':len(financial['quarterly']),
        'latest_quarter':financial['quarterly'][-1]['period'],
        'trends_evaluated':trends.get('evaluated_pairs',0),
        'significant_trends':trends.get('detected_pairs',0),
        'paid_api_calls':0
    },ensure_ascii=False))


if __name__=='__main__':
    build()
