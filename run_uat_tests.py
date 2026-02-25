"""Run all 41 UAT tests for MetaPM v2.4.0 programmatically."""
import urllib.request, json, sys
from collections import Counter

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE = 'https://metapm.rentyourcio.com'

def get(path, timeout=15):
    resp = urllib.request.urlopen(f'{BASE}{path}', timeout=timeout)
    return json.loads(resp.read())

# Get all data
health = get('/health')
reqs_data = get('/api/requirements?limit=200')
reqs = reqs_data.get('requirements', [])
sprints_data = get('/api/sprints')
sprints = sprints_data.get('sprints', [])
projects_data = get('/api/roadmap/projects')
projects = projects_data.get('projects', [])

code_map = {}
for r in reqs:
    code_map.setdefault(r['code'], []).append(r)

def get_req(code):
    items = code_map.get(code, [])
    return items[0] if items else None

def check_absent(code):
    return code not in code_map

def check_desc_contains(code, *terms):
    r = get_req(code)
    if not r:
        return False
    desc = (r.get('description', '') or '').lower()
    return all(t.lower() in desc for t in terms)

results = []

# ===== FUNCTIONAL TESTS =====
v = health.get('version', '')
results.append(('FUN-01', 'Version deployed', v == '2.4.0', f'Got {v} (deploy pending PL)'))

mp001 = get_req('MP-001')
r = mp001 is None or mp001.get('status') == 'done'
detail = f'status={mp001["status"]}' if mp001 else 'absent'
results.append(('FUN-02', 'MP-001 deleted/done', r, detail))

results.append(('FUN-03', 'SF-009 absent', check_absent('SF-009'), ''))

for tid, code in [('FUN-04','PM-005'),('FUN-05','EM-005'),('FUN-06','EM-002'),('FUN-07','HL-014'),('FUN-08','HL-018')]:
    r = get_req(code)
    status = r['status'] if r else 'NOT FOUND'
    results.append((tid, f'{code} closed', status == 'done', f'status={status}'))

results.append(('FUN-09', 'SF-001 deleted (merged)', check_absent('SF-001'), ''))

results.append(('FUN-10', 'SF-008 desc updated', check_desc_contains('SF-008', 'performance stats', 'per-user data'), ''))

new_items = [
    ('FUN-11','SF-019','bug','P1'),('FUN-12','SF-020','bug','P1'),
    ('FUN-13','SF-021','bug','P3'),('FUN-14','SF-022','bug','P2'),
    ('FUN-15','SF-023','feature','P2'),('FUN-16','SF-024','feature','P2'),
    ('FUN-17','SF-025','feature','P2'),('FUN-18','SF-026','feature','P2'),
    ('FUN-19','AF-031','feature','P2'),('FUN-20','AF-032','feature','P2'),
]
for tid, code, typ, pri in new_items:
    r = get_req(code)
    ok = r is not None
    detail = f'type={r.get("type","?")},pri={r.get("priority","?")}' if r else 'NOT FOUND'
    results.append((tid, f'{code} exists', ok, detail))

desc_checks = [
    ('FUN-21', 'MP-011', ['Multi-select', 'hierarchical']),
    ('FUN-22', 'MP-012', ['siblings of requirements']),
    ('FUN-23', 'MP-013', ['audit trail']),
    ('FUN-24', 'SF-002', ['arrow', 'inverted']),
    ('FUN-25', 'SF-013', ['Etymology Family Graph']),
    ('FUN-26', 'SF-014', ['header bar']),
    ('FUN-27', 'HL-016', ['NOT a melody quiz']),
    ('FUN-28', 'HL-017', ['NOT MIDI keyboard']),
]
for tid, code, terms in desc_checks:
    ok = check_desc_contains(code, *terms)
    results.append((tid, f'{code} desc updated', ok, ''))

total = len(reqs)
results.append(('FUN-29', 'Total req count', total == 114, f'Got {total}'))

proj_counts = Counter(r.get('project_name', '') for r in reqs)
expected = {'ArtForge':32,'Etymython':12,'HarmonyLab':16,'MetaPM':25,'Super-Flashcards':24,'project-methodology':5}
count_ok = all(proj_counts.get(k, 0) == v for k, v in expected.items())
results.append(('FUN-30', 'Count by project', count_ok, str(dict(sorted(proj_counts.items())))))

# ===== REGRESSION TESTS =====
results.append(('REG-01', 'API /requirements responds', len(reqs) > 0, f'{len(reqs)} items'))
results.append(('REG-02', 'API /projects responds', len(projects) > 0, f'{len(projects)} projects'))
results.append(('REG-03', 'API /sprints responds', len(sprints) > 0, f'{len(sprints)} sprints'))

try:
    search = get('/api/requirements?search=chord&limit=200')
    search_reqs = search.get('requirements', [])
    results.append(('REG-04', 'Search works', True, f'{len(search_reqs)} results'))
except Exception as e:
    results.append(('REG-04', 'Search works', False, str(e)[:60]))

for code in ['AF-016', 'AF-017']:
    r = get_req(code)
    results.append(('REG-05', f'{code} intact', r is not None, ''))

for code in ['HL-008', 'HL-012']:
    r = get_req(code)
    results.append(('REG-06', f'{code} intact', r is not None, ''))

for code in ['EM-012', 'EM-008']:
    r = get_req(code)
    results.append(('REG-07', f'{code} intact', r is not None, ''))

# ===== DATA INTEGRITY TESTS =====
efg = any(p.get('code') == 'EFG' for p in projects)
results.append(('DATA-01', 'Etymology Family Graph project', efg, ''))

pf = any('PromptForge' in p.get('name', '') or p.get('code') == 'PROMPTFORG' for p in projects)
results.append(('DATA-02', 'PromptForge project', pf, ''))

results.append(('DATA-03', '10 mega sprints exist', len(sprints) >= 10, f'{len(sprints)} sprints'))

orphans = [r for r in reqs if not r.get('project_id')]
results.append(('DATA-04', 'No orphaned requirements', len(orphans) == 0, f'{len(orphans)} orphans'))

# ===== SUMMARY =====
passed = sum(1 for _, _, ok, _ in results if ok)
failed = sum(1 for _, _, ok, _ in results if not ok)
print(f'\n{"=" * 64}')
print(f'UAT RESULTS: {passed} PASSED, {failed} FAILED (out of {len(results)} tests)')
print(f'{"=" * 64}\n')

for tid, desc, ok, detail in results:
    status = 'PASS' if ok else 'FAIL'
    extra = f' ({detail})' if detail else ''
    print(f'  {status} {tid}: {desc}{extra}')

print(f'\nTotal checks: {len(results)}')
