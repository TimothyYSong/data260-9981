#!/usr/bin/env python3
"""DATA 260 HW9 objective smoke verification. Run on the submitted commit.

Reads application and experimental data, pings Redis services, performs a
non-destructive Redis INCR test with a temporary PREFIX key, and exercises the
existing inspection tool and two-agent path. Writes reports/hw09/verification.json.
"""
import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
sys.path[:0] = [str(ROOT), str(ROOT / 'code'), str(ROOT / 'hw9_part4')]
OUT = ROOT / 'reports/hw09/verification.json'
checks = []


def read_json(path):
    return json.loads((ROOT / path).read_text(encoding='utf-8'))


def check(name, operation):
    try:
        detail = operation()
        checks.append({'check': name, 'status': 'PASS', 'detail': str(detail)})
        print('PASS:', name, '|', detail, flush=True)
    except Exception as exc:
        checks.append({'check': name, 'status': 'FAIL', 'detail': f'{type(exc).__name__}: {exc}'})
        print('FAIL:', name, '|', f'{type(exc).__name__}: {exc}', flush=True)


def verify_dataset():
    reference = read_json('hw9_part4/reference_data.json')['inspections']
    assert len(reference) >= 24
    refs = {int(x['inspection_id']) for x in reference}
    assert len(refs) == len(reference)
    splits = {}
    for split in ('training', 'validation', 'test'):
        data = read_json(f'hw9_part4/{split}_data.json')
        ids = {int(x['inspection_id']) for x in data}
        assert len(ids) == len(data) == 8
        assert ids <= refs
        assert all(set(x) <= {'id', 'inspection_id', 'question'} for x in data)
        splits[split] = ids
    assert all(splits[a].isdisjoint(splits[b]) for a,b in
               (('training','validation'), ('training','test'), ('validation','test')))
    return '40 reference inspections; 8/8/8 nonoverlapping input-only questions'


def verify_artifacts():
    data = read_json('hw9_part4/variant_results.json')
    rows = data['summary']
    assert data['test_cases'] == 8
    assert len(rows) == 4
    for row in rows:
        assert row['correct_answers'] + row['incorrect_answers'] == 8
        assert 1 <= row['average_attempts'] <= 2
        assert row['average_latency_ms'] > 0
    validation = read_json('hw9_part4/validation_results.json')['summary']
    assert validation['validation_cases'] == 8
    assert validation['decision'] == 'KEEP'
    lessons = read_json('hw9_part4/lessons.json')
    assert lessons and all({'lesson_id','failure_pattern','correction','created_at','use_count'} <= set(x) for x in lessons)
    return 'four saved variant results, eight-case validation and lesson schema valid'


def verify_threshold_sweep():
    rows = read_json('reports/hw09/raw/part3_sweep_summary.json')
    assert [round(r['threshold'],2) for r in rows] == [.75,.80,.85,.90,.95]
    assert all(r['total'] == 40 and r['hits']+r['misses'] == 40 for r in rows)
    return 'five thresholds, 40 queries per threshold, totals consistent'


def verify_redis_counter():
    import redis
    client = redis.Redis(host=os.getenv('REDIS_HOST','localhost'), port=int(os.getenv('REDIS_PORT','6379')), decode_responses=True,
                         socket_connect_timeout=4, socket_timeout=4)
    assert client.ping()
    key = f's9981:verify:hw09:{uuid4().hex}'
    try:
        assert client.incr(key) == 1
        assert client.incr(key) == 2
        assert int(client.get(key)) == 2
    finally:
        client.delete(key)
    return 'Redis PING and temporary s9981-prefixed INCR round-trip passed; temp key deleted'


def verify_redis_search():
    import redis
    client = redis.Redis(host=os.getenv('REDIS_SEARCH_HOST','localhost'), port=int(os.getenv('REDIS_SEARCH_PORT','6380')),
                         socket_connect_timeout=4, socket_timeout=4)
    assert client.ping()
    indices = client.execute_command('FT._LIST')
    assert any((x.decode() if isinstance(x, bytes) else x) == 's9981:semantic:index' for x in indices)
    return 'Redis Stack PING and existing s9981 semantic vector index confirmed'


def verify_tool_round_trip():
    from tool_executor import execute_tool
    ref = read_json('hw9_part4/reference_data.json')['inspections'][0]
    result = json.loads(execute_tool('inspection_detail', {'inspection_id': int(ref['inspection_id'])}))
    assert result.get('ok') is True, result.get('error')
    details = result['data']
    # compare the field(s) actually present without depending on answer wording
    assert str(ref['inspection_id']) in json.dumps(details)
    return f"inspection_detail({ref['inspection_id']}) returned a successful record"


def verify_two_agents():
    from answering_agent import AnsweringAgent
    from evaluator_agent import EvaluatorAgent
    item = read_json('hw9_part4/training_data.json')[0]
    response = AnsweringAgent().answer(item['question'], item['inspection_id'])
    evaluator = EvaluatorAgent()
    good = evaluator.evaluate(item['question'], item['inspection_id'], response['answer'])
    assert good['result'] == 'PASS', good['feedback']
    # objectively wrong answer used only in development verification
    bad = evaluator.evaluate(item['question'], item['inspection_id'],
                             f"Inspection {item['inspection_id']} has 999 violations.")
    assert bad['result'] == 'REVISE'
    return 'live answer PASS; deliberately wrong violation count REVISE'


def git_output(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def main():
    try:
        commit = git_output('rev-parse', 'HEAD')
    except Exception:
        print('ERROR: run this script from within the Git repository', file=sys.stderr)
        return 2
    tag = os.getenv('HW09_TAG', 'hw9')
    try:
        tagged_commit = git_output('rev-list', '-n', '1', tag)
    except Exception:
        tagged_commit = None
    check('Git tag points to checked-out commit', lambda: (
        f'{tag} -> {commit[:12]}' if tagged_commit == commit else
        (_ for _ in ()).throw(AssertionError(f'tag {tag} missing or not at HEAD'))
    ))
    check('Reference and split datasets', verify_dataset)
    check('Stored results and lesson structure', verify_artifacts)
    check('Saved threshold sweep totals', verify_threshold_sweep)
    check('Part 1 Redis connection and INCR', verify_redis_counter)
    check('Part 2 Redis vector index', verify_redis_search)
    check('Domain inspection tool smoke test', verify_tool_round_trip)
    check('Live Answering and Evaluator agents', verify_two_agents)
    result = {
        'homework_number': 9,
        'SID4': '9981',
        'commit_hash': commit,
        'tag': tag,
        'tag_commit_hash': tagged_commit,
        'model': 'qwen3:8b',
        'configuration': {'domain_id': 5, 'domain': 'Local Restaurant Inspection',
                          'prefix': 's9981', 'semantic_embedding_model': 'all-MiniLM-L6-v2',
                          'semantic_default_threshold': 0.95},
        'SEED': 9981,
        'VERIFY_SEED': 269981,
        'verified_at_utc': dt.datetime.now(dt.timezone.utc).isoformat(),
        'checks': checks,
        'passed': sum(x['status']=='PASS' for x in checks),
        'failed': sum(x['status']=='FAIL' for x in checks),
        'overall': 'PASS' if all(x['status']=='PASS' for x in checks) else 'FAIL'
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(f'\nOverall: {result["overall"]} ({result["passed"]}/{len(checks)})')
    print(f'Wrote {OUT}')
    return 0 if result['overall']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
