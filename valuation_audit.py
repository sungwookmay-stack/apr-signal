"""Independent checks of reviewed valuation inputs against saved OpenDART data.
A match verifies only the named amount, not shares, EPS or attributable profit.
"""

def reconcile(source, dart):
    filings={x['period']:x for x in dart.get('filings',[])}
    rows=[]
    for kind, observations, key, account in (
        ('balance', source.get('balance',[]), 'equity', 'equity'),
        ('annual', source.get('annual',[]), 'net_income', 'net_income'),
        ('quarterly', source.get('quarterly',[]), 'ni', 'net_income'),
    ):
        for x in observations:
            filing=filings.get(x['period'],{})
            observed=filing.get('accounts',{}).get(account,{}).get('value_won')
            # Fourth-quarter profit is not the annual amount. It needs a YTD subtraction.
            if x['period'].endswith('Q4'): observed=None
            reviewed=x.get(key)
            delta=None if observed is None or reviewed is None else reviewed-observed/1e8
            receipts=filing.get('receipt_numbers',[])
            rows.append({'period':x['period'],'kind':kind,'account':account,
                         'input_100m':reviewed,'dart_100m':None if observed is None else observed/1e8,
                         'difference_100m':delta,
                         'status':'unverified' if delta is None else ('match_rounding' if abs(delta)<=.02 else 'mismatch'),
                         'source_url':('https://dart.fss.or.kr/dsaf001/main.do?rcpNo='+receipts[0]) if receipts else None})
    return {'checked_at_utc':dart.get('checked_at_utc'), 'rows':rows,
            'note':'DART 저장값과 연결 순이익·총자본 금액만 대조. 지배주주 지분, EPS, 주식수 및 최초 발표시점 검증을 의미하지 않음. 차이는 자동 덮어쓰지 않음.'}
