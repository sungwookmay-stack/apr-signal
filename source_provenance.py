"""Normalize display provenance of saved observations without recollecting data."""
import json
from pathlib import Path

KBTY_NOTE = ('가격: Yahoo Finance 비공식 일별시세. AUM: 운용사 페이지 제한적 추출 또는 출처 기록 CSV. '
             'NAV·APR 보유비중·보유주식수: 수동 검증 CSV 입력(자동 수집 아님). 미확인 항목은 null.')

def normalize_saved_sources(root):
    root = Path(root)
    for name in ('flows', 'kbty'):
        path = root / (name + '.json')
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if name == 'kbty':
            data['source_note'] = KBTY_NOTE
        else:
            data['source_scope'] = '투자자 수급·공매도·대차는 별도 자료이며 각 관측의 source/source_url 및 기준일을 따름'
            status = data.setdefault('data_status', {})
            latest = data.get('latest_daily') or {}
            loan = (data.get('lending') or {}).get('latest') or {}
            status['primary_source'] = latest.get('source', '미수집')
            status['flow_source_url'] = latest.get('source_url')
            status['lending_source_url'] = loan.get('source_url')
            status['warning'] = ('KRX 범위와 NXT 포함 여부·거래시간 구분을 원천 자료와 대조. '
                                 '관측별 unit·amount_estimated로 실제 거래대금과 주수×종가 추정을 구분. '
                                 '연기금은 기관 합계의 부분집합')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
