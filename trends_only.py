"""Refresh only Google Trends without re-running the broader APR collector."""
import collections
import datetime as dt
import json
import os
from pathlib import Path

from optional_free_api import Budget, terms_for_country, update_trends
from trend_signals import detect

ROOT = Path(__file__).resolve().parent
DATA = ROOT / 'data'
PREFIX = 'window.APR_BOOTSTRAP = '


def write(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(data, encoding='utf-8')
    tmp.replace(path)


def dump(path, data):
    write(path, json.dumps(data, ensure_ascii=False, indent=2) + '\n')


def bounds(rows):
    return (max((r['date'] for r in rows if not r.get('partial')), default=''),
            max((r['date'] for r in rows), default=''))


def validated(old, candidate, config, today):
    prior, incoming = collections.defaultdict(list), collections.defaultdict(list)
    for r in old:
        prior[r['country']].append(r)
    for r in candidate:
        incoming[r['country']].append(r)
    complete = {}
    for market in config['markets']:
        cc = market['code']
        rows = incoming[cc]
        expected_id = f'API.SH_{cc}_{today}'
        new_bounds, old_bounds = bounds(rows), bounds(prior[cc])
        terms = set(terms_for_country(config, cc))
        keys = {(r['date'], r['term']) for r in rows}
        parsed = set(r['term'] for r in rows)
        if (not rows or rows == prior[cc] or
                {r.get('dataset') for r in rows} != {expected_id} or
                new_bounds[0] <= old_bounds[0] or new_bounds[1] < old_bounds[1] or
                new_bounds[1] > today or len(keys) != len(rows) or parsed != terms or
                len(rows) < 0.9 * len(prior[cc])):
            continue
        complete[cc] = rows
    return [r for r in old if r['country'] not in complete] + [
        r for rows in complete.values() for r in rows], complete


def result(value):
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write(f'result={value}\n')


def run():
    demand_path = DATA / 'demand.json'
    status_path = DATA / 'status.json'
    bootstrap_path = DATA / 'bootstrap.js'
    demand = json.loads(demand_path.read_text(encoding='utf-8'))
    status = json.loads(status_path.read_text(encoding='utf-8'))
    raw = bootstrap_path.read_text(encoding='utf-8')
    if not raw.startswith(PREFIX) or not raw.strip().endswith(';'):
        raise RuntimeError('Invalid existing bootstrap; stopped before API calls')
    bootstrap = json.loads(raw.strip()[len(PREFIX):-1])
    config = json.loads((ROOT / 'config/markets.json').read_text(encoding='utf-8'))
    markets = config['markets']
    eligible = len(markets)
    key = os.environ.get('APISH_KEY', '').strip()
    if not key:
        raise RuntimeError('Existing Google Trends connection is not configured')
    client = Budget(key)
    today = client.today.isoformat()
    if client.stats.get('last_trends_run_day') == today:
        print('Google Trends collection already attempted today; no repeat.')
        result('already_attempted')
        return
    if client.remaining() < eligible:
        raise RuntimeError('Existing free-credit ledger cannot cover a complete market batch')
    old = demand['trends']
    incoming, _ = update_trends(client, config, old, force_today=True)
    rows, updated = validated(old, incoming, config, today)
    print(json.dumps({'attempted_date_kst': today, 'updated_markets': {
        cc: bounds(rr) for cc, rr in sorted(updated.items())}, 'retained_markets': [
        m['code'] for m in markets if m['code'] not in updated],
        'monthly_attempted_credits': client.stats.get('attempted_credits', 0)}, ensure_ascii=False))
    if not updated:
        print('No newer validated market series. Retaining prior observations and recording attempted credits.')
        result('no_new_observations')
        return
    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    demand['trends'] = rows
    demand['updated_at'] = now
    demand['api_credits_used_this_month'] = client.stats['attempted_credits']
    demand['trends_status'] = [f'API.SH Google Trends: {len(updated)}/{eligible}개국 새 확정 관측 반영']
    if len(updated) != eligible:
        demand['trends_status'].append('기존값 유지: ' + ', '.join(
            m['code'] for m in markets if m['code'] not in updated))
    marks = {m['code']: bounds([r for r in rows if r['country'] == m['code']]) for m in markets}
    status['trends_points'] = len(rows)
    status['trends_last_complete_by_country'] = {cc: d[0] or None for cc, d in marks.items()}
    status['trends_last_observed_by_country'] = {cc: d[1] or None for cc, d in marks.items()}
    status['trends_checked_at_utc'] = now
    signals = detect(rows, demand['countries'])
    bootstrap.update(demand=demand, status=status, trend_signals=signals)
    dump(demand_path, demand)
    dump(status_path, status)
    dump(DATA / 'trend_signals.json', signals)
    write(bootstrap_path, PREFIX + json.dumps(bootstrap, ensure_ascii=False, separators=(',', ':')) + ';\n')
    result('updated')


if __name__ == '__main__':
    run()
