"""APR technical analysis -- no dependencies, no look-ahead signals.

Daily KRW OHLC data only. Trading indicators are descriptive filters,
NOT an investment order or guaranteed predictive result.

Ichimoku cloud at candle t uses spans formed 26 sessions earlier, so it does
not compare today's price to *future* cloud values. Displaced future cloud
values are emitted separately for optional chart projection.
"""
from __future__ import annotations
from math import sqrt
from statistics import pstdev


def sma(v, n):
    return [sum(v[i-n+1:i+1])/n if i+1>=n and all(x is not None for x in v[i-n+1:i+1]) else None for i in range(len(v))]


def ema(v,n):
    out=[None]*len(v); last=None; k=2/(n+1)
    for i,x in enumerate(v):
        if x is None: continue
        if last is None:
            if i+1>=n and all(z is not None for z in v[i-n+1:i+1]):last=sum(v[i-n+1:i+1])/n
        else:last=x*k+last*(1-k)
        out[i]=last
    return out


def rsi(close,n=14):
    out=[None]*len(close)
    if len(close)<n+1:return out
    diffs=[close[i]-close[i-1] for i in range(1,len(close))]
    gains=[max(0,d) for d in diffs]; losses=[max(0,-d) for d in diffs]
    avg_gain=sum(gains[:n])/n;avg_loss=sum(losses[:n])/n
    def value(g,l):return 50.0 if g==0 and l==0 else (100.0 if l==0 else 100-100/(1+g/l))
    out[n]=value(avg_gain,avg_loss)
    for i in range(n+1,len(close)):
        avg_gain=(avg_gain*(n-1)+gains[i-1])/n
        avg_loss=(avg_loss*(n-1)+losses[i-1])/n
        out[i]=value(avg_gain,avg_loss)
    return out


def midpoint(high,low,n):
    out=[]
    for i in range(len(high)):
        hs=high[i-n+1:i+1];ls=low[i-n+1:i+1]
        out.append((max(hs)+min(ls))/2 if i+1>=n and all(x is not None for x in hs+ls) else None)
    return out


def atr(high,low,close,n=14):
    tr=[]
    for i,(h,l,c) in enumerate(zip(high,low,close)):
        if h is None or l is None or c is None:tr.append(None)
        elif i==0:tr.append(h-l)
        else:tr.append(max(h-l,abs(h-close[i-1]),abs(l-close[i-1])))
    out=[None]*len(close)
    if len(tr)<n or any(x is None for x in tr[:n]):return out
    v=sum(tr[:n])/n;out[n-1]=v
    for i in range(n,len(tr)):
        if tr[i] is None:continue
        v=(v*(n-1)+tr[i])/n;out[i]=v
    return out


def calculate(rows):
    clean=[r for r in rows if isinstance(r.get('close_krw'),(int,float)) and r.get('date')]
    clean.sort(key=lambda r:r['date'])
    # Guard duplicated dates and corrupt OHLC. Invalid H/L -> Ichimoku unavailable on those sessions.
    series={r['date']:r for r in clean};clean=[series[d] for d in sorted(series)]
    close=[float(r['close_krw']) for r in clean]
    high=[float(r['high_krw']) if r.get('high_krw') is not None else None for r in clean]
    low=[float(r['low_krw']) if r.get('low_krw') is not None else None for r in clean]
    vol=[float(r.get('volume') or 0) or None for r in clean]
    m20=sma(close,20);m60=sma(close,60);m200=sma(close,200)
    v20=sma(vol,20)
    bb_std=[pstdev(close[i-19:i+1]) if i>=19 else None for i in range(len(close))]
    bb_u=[a+2*b if a is not None and b is not None else None for a,b in zip(m20,bb_std)]
    bb_l=[a-2*b if a is not None and b is not None else None for a,b in zip(m20,bb_std)]
    e12=ema(close,12);e26=ema(close,26)
    macd=[a-b if a is not None and b is not None else None for a,b in zip(e12,e26)]
    signal=ema(macd,9)
    hist=[a-b if a is not None and b is not None else None for a,b in zip(macd,signal)]
    tenkan=midpoint(high,low,9);kijun=midpoint(high,low,26)
    spanb_raw=midpoint(high,low,52)
    spana_raw=[(a+b)/2 if a is not None and b is not None else None for a,b in zip(tenkan,kijun)]
    # The cloud on screen at t consists of the spans calculated at t-26.
    cloud_a=[spana_raw[i-26] if i>=26 else None for i in range(len(close))]
    cloud_b=[spanb_raw[i-26] if i>=26 else None for i in range(len(close))]
    strength=rsi(close);volat=atr(high,low,close)
    out=[]
    for i,r in enumerate(clean):
        def roundn(v,k=2):return round(v,k) if v is not None else None
        out.append({'date':r['date'],'close':close[i],
          'ma20':roundn(m20[i]),'ma60':roundn(m60[i]),'ma200':roundn(m200[i]),
          'bb_upper':roundn(bb_u[i]),'bb_mid':roundn(m20[i]),'bb_lower':roundn(bb_l[i]),
          'rsi14':roundn(strength[i]),'macd':roundn(macd[i],4),'macd_signal':roundn(signal[i],4),
          'macd_hist':roundn(hist[i],4),'tenkan':roundn(tenkan[i]),'kijun':roundn(kijun[i]),
          'cloud_a':roundn(cloud_a[i]),'cloud_b':roundn(cloud_b[i]),
          'volume_ratio20':roundn(vol[i]/v20[i]) if vol[i] and v20[i] else None,
          'atr14':roundn(volat[i])})
    latest=out[-1] if out else None
    prev=out[-2] if len(out)>1 else None
    checks=[];score=0
    def check(text,ok,points=1,detail=''):
        nonlocal score
        if ok is None:status='unknown'
        else:
            status='positive' if ok else 'negative'
            score+=points if ok else -points
        checks.append({'name':text,'status':status,'detail':detail})
    if latest:
        fully_ready=(len(out)>=200 and latest.get('ma200') is not None and
                     latest.get('cloud_a') is not None and latest.get('cloud_b') is not None and
                     latest.get('bb_upper') is not None and latest.get('rsi14') is not None and
                     latest.get('macd_hist') is not None and latest.get('atr14') is not None)
        c=latest['close']; a=latest['cloud_a'];b=latest['cloud_b']; r=latest['rsi14']
        check('일목 구름 기준 추세', c>max(a,b) if a is not None and b is not None else None,2,
              '현 종가와 현재 구름을 비교 (26거래일 전 형성된 선행스팬)')
        check('전환선·기준선 배열', latest['tenkan']>latest['kijun'] if latest['tenkan'] is not None and latest['kijun'] is not None else None,1,
              '전환선 > 기준선이면 단기 추세 우위')
        check('20일 이동평균 위', c>latest['ma20'] if latest['ma20'] is not None else None,1)
        check('60일 이동평균 위', c>latest['ma60'] if latest['ma60'] is not None else None,1)
        check('200일 이동평균 위', c>latest['ma200'] if latest['ma200'] is not None else None,1)
        check('MACD 시그널 우위', latest['macd_hist']>0 if latest['macd_hist'] is not None else None,1)
        check('RSI 중립~강세 구간', 40<=r<=70 if r is not None else None,1,
              'RSI > 70 과열 가능, < 30 과매도 가능 (단독 진입 신호 아님)')
        # Entry not signaled on RSI oversold or lower band breach alone.
        cloud_ok=(a is not None and b is not None and c>max(a,b))
        trend_ok=cloud_ok and (latest['ma200'] is None or c>latest['ma200'])
        rsi_up=(r is not None and prev and prev['rsi14'] is not None and r>prev['rsi14'])
        bb_reentry=(prev and prev['bb_lower'] is not None and latest['bb_lower'] is not None and
                    prev['close']<prev['bb_lower'] and c>latest['bb_lower'])
        pullback=(latest['ma20'] is not None and latest['ma20']*0.97<=c<=latest['ma20']*1.03)
        candidate_buy=(fully_ready and score>=5 and latest['macd_hist'] is not None and latest['macd_hist']>0 and r is not None and r<75)
        candidate_sell=(fully_ready and (score<=-3 or (a is not None and b is not None and c<min(a,b) and latest['macd_hist'] is not None and latest['macd_hist']<0)))
        candidate_add=bool(fully_ready and trend_ok and rsi_up and (bb_reentry or pullback) and latest['macd_hist'] is not None and latest['macd_hist']>=0)
        if not fully_ready:label='분석 유보 / OHLC 200거래일 필요';kind='unknown'
        elif candidate_sell:label='하락 위험 / 매도·비중축소 검토';kind='risk'
        elif candidate_buy:label='상승 추세 / 분할매수 관찰';kind='watch_buy'
        else:label='중립 / 확인 대기';kind='neutral'
        if c>latest['bb_upper'] if latest['bb_upper'] is not None else False:
            checks.append({'name':'볼린저 상단 돌파','status':'caution','detail':'상승 모멘텀 또는 단기 과열. 추격 매수 경계'})
        if c<latest['bb_lower'] if latest['bb_lower'] is not None else False:
            checks.append({'name':'볼린저 하단 이탈','status':'caution','detail':'변동성 확대. 하단 이탈만으로 물타기 신호 아님'})
        if r is not None and r>=75:
            checks.append({'name':'RSI 과열 주의','status':'caution','detail':'추격 매수 위험'})
        latest_summary={
          'date':latest['date'],'label':label,'kind':kind,'score':score,'checks':checks,
          'averaging_down':('자료 부족으로 추가매수 신호 유보' if not fully_ready else ('추가매수 조건부 관찰' if candidate_add else '추가매수 보류 / 추가 확인 필요')),
          'add_criteria':'구름 상단·장기추세 위 + RSI 반등 + 볼린저 하단 복귀 또는 20일선 부근 + MACD 음(-)이 아님',
          'risk_reference':round(c-2*latest['atr14']) if latest['atr14'] is not None else None,
          'risk_note':'종가 - 2×ATR은 변동성 참고 가격이며 손절 주문 가격을 뜻하지 않습니다.',
          'overheat':bool((r and r>=75) or (latest['bb_upper'] is not None and c>latest['bb_upper'])),
          'not_advice':True,'fully_ready':fully_ready,
        }
    else:latest_summary={'label':'시세 없음','kind':'unknown','checks':[],'date':None}
    return {'method':'2026-11; SMA20/60/200 BB20±2σ RSI14 MACD12/26/9 Ichimoku9/26/52 shift26 ATR14','series':out,
      'last':latest_summary,'valid_high_low':sum(x is not None for x in high),
      'data_days':len(out),'has_real_data':bool(out)}
