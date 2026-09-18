"""Regenerate the maintained mapping overview without probing the host."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from devprep.catalog import load_catalog
from devprep.planner import build_plan
from devprep.platforms import Host, MANAGERS

catalog = load_catalog()
lines = ['# Catalog mappings', '', 'Generated from `devprep/catalog.json` by `python scripts/update_catalog_docs.py`.', '',
         '`native` = mapped package(s); `recipe` = maintained user-local installer; `included` = bundled with another selected tool; `n/a` = platform does not apply; `—` = no maintained mapping.', '',
         'A native mapping is a candidate package name, not a guarantee for every OS release or configured repository. Download recipes also depend on upstream platform requirements. Linux previews use x86_64; architecture restrictions still apply.', '',
         '| Tool | ' + ' | '.join(MANAGERS) + ' |', '| --- | ' + ' | '.join('---' for _ in MANAGERS) + ' |']
for tool in catalog['tools']:
    states=[]
    for manager in MANAGERS:
        system='windows' if manager=='winget' else 'macos' if manager=='brew' else 'linux'
        step=build_plan(Host(system, 'preview', 'x86_64', manager), [tool]).steps[0]
        states.append('native' if step.commands else 'recipe' if step.recipe else 'included' if step.reason.startswith('included') else 'n/a' if step.reason.startswith('not applicable') else '—')
    lines.append('| `'+tool['id']+'` | '+' | '.join(states)+' |')
(ROOT / 'docs/catalog.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
