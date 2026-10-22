#!/usr/bin/env python3
"""Bundle the generated scene plugin as an installable local marketplace."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "scene-assets"
MARKET = ROOT / "dist" / "scene-assets-local-marketplace"
OUTPUT = ROOT / "dist" / "scene-assets-local-marketplace.zip"

if not (PLUGIN / ".codex-plugin" / "plugin.json").is_file():
    raise SystemExit("Build scene-assets before packaging its local marketplace")
if MARKET.exists():
    shutil.rmtree(MARKET)
if OUTPUT.exists():
    OUTPUT.unlink()
target = MARKET / "plugins" / "scene-assets"
shutil.copytree(PLUGIN, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".venv"))
manifest = {"name": "scene-assets-local", "interface": {"displayName": "场景资产 Local"},
            "plugins": [{"name": "scene-assets",
                         "source": {"source": "local", "path": "./plugins/scene-assets"},
                         "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
                         "category": "Productivity"}]}
path = MARKET / ".agents" / "plugins" / "marketplace.json"
path.parent.mkdir(parents=True, exist_ok=True)
path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
with zipfile.ZipFile(OUTPUT, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for file in MARKET.rglob("*"):
        if file.is_file():
            archive.write(file, Path(MARKET.name) / file.relative_to(MARKET))
print(MARKET)
print(OUTPUT)
