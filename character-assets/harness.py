#!/usr/bin/env python3
"""Portable launcher; dependencies are explicit and hash locked."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parent
if sys.version_info<(3,12):
    raise SystemExit('Python 3.12+ required. Select a compatible interpreter; this tool does not modify Codex configuration.')
if any(importlib.util.find_spec(name) is None for name in ('jsonschema','yaml')):
    key=hashlib.sha256((ROOT/'requirements.lock').read_bytes()).hexdigest()[:16]
    suffix=Path('Scripts/python.exe') if os.name=='nt' else Path('bin/python')
    candidates=[ROOT/'.venv'/suffix,Path.home()/'.cache/harness-runtime'/key/f'py{sys.version_info.major}{sys.version_info.minor}'/suffix]
    current_environment=Path(sys.prefix).resolve()
    # POSIX venv binaries may correctly symlink to the very same standalone
    # base Python while sys.prefix/site-packages identify different environments.
    # Compare environment roots, not real executable bytes. Track attempted
    # roots across exec so two incomplete environments cannot bounce forever.
    chain_key='HARNESS_LAUNCHER_TRIED_ENVIRONMENTS'
    try:
        chain=json.loads(os.environ.get(chain_key,'[]'))
        tried=set(chain) if isinstance(chain,list) and all(isinstance(value,str) for value in chain) else set()
    except (ValueError,TypeError):
        tried=set()
    tried.add(str(current_environment))
    candidate=next((path for path in candidates if path.is_file() and
                    path.parent.parent.resolve()!=current_environment and
                    str(path.parent.parent.resolve()) not in tried),None)
    if candidate:
        tried.add(str(candidate.parent.parent.resolve()))
        os.environ[chain_key]=json.dumps(sorted(tried))
        os.execv(str(candidate),[str(candidate),str(Path(__file__).resolve()),*sys.argv[1:]])
    raise SystemExit(f'Dependencies are missing. Run: "{sys.executable}" "{ROOT / "scripts/bootstrap.py"}" --install')
sys.path.insert(0,str(ROOT/'runtime'))
from harness_core.cli import main
raise SystemExit(main(ROOT))
