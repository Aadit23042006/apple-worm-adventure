"""Source-derived reachability smoke check for deterministic level layouts.

This executes the project's actual level_objectives/level_static_config AST nodes.
It intentionally checks static grid connectivity only; it is not full worm-body
or move-sequence gameplay proof.
"""
import ast
from collections import deque
from pathlib import Path

source = Path('backend/core/views.py').read_text(encoding='utf-8')
tree = ast.parse(source)
wanted = {'level_objectives', 'level_static_config'}
nodes = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in wanted]
if {n.name for n in nodes} != wanted:
    raise SystemExit('Could not locate actual project level configuration functions.')
module = ast.Module(body=nodes, type_ignores=[])
ns = {'min': min, 'max': max, 'int': int, 'dict': dict, 'range': range}
exec(compile(module, 'backend/core/views.py', 'exec'), ns)


def reachable(size, blocked, start, goal):
    queue = deque([start])
    seen = {start}
    while queue:
        r, c = queue.popleft()
        if (r, c) == goal:
            return True
        for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            p = (nr, nc)
            if not (0 < nr < size-1 and 0 < nc < size-1):
                continue
            if p in blocked or p in seen:
                continue
            seen.add(p)
            queue.append(p)
    return False

passed = 0
failures = []
for level in range(1, 61):
    cfg = ns['level_static_config'](level)
    blocked = {(p['r'], p['c']) for p in cfg['obstacles']}
    start = (1, 1)
    targets = [(p['r'], p['c']) for p in cfg['apples']] + [(cfg['portal']['r'], cfg['portal']['c'])]
    ok = all(reachable(cfg['size'], blocked, start, target) for target in targets)
    if ok:
        passed += 1
    else:
        failures.append(level)
print(f'PASS: {passed}/60 layouts have a reachable apple set and portal (static grid connectivity).')
if failures:
    print('FAILURES:', failures)
    raise SystemExit(1)
