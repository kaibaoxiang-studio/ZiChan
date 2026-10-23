#!/bin/bash
set -euo pipefail
cd -- "$(dirname -- "$0")/.."
python3 -B scene-plugin-maintenance/package_plugin.py --check
python3 -B -m unittest discover -s scene-plugin-maintenance/tests -v
python3 -B scene-assets/skills/sence-prompts/scripts/check_skill_files.py scene-assets/skills/sence-prompts
python3 -B -m unittest discover -s scene-assets/skills/sence-prompts/tests -p 'test_*.py' -v
