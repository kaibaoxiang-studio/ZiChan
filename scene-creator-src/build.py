#!/usr/bin/env python3
"""Build and safely update the standalone scene-assets plugin."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path(__file__).resolve().parent
CONTENT = SOURCE / "plugin_files"
VERSION = "0.1.0"


def schema(properties, required=()):
    return {"type": "object", "properties": properties, "required": list(required),
            "additionalProperties": False}


def text_field():
    return {"type": "string", "minLength": 1}


RESULT = schema({"status": {"type": "string"}, "artifact_path": {"type": "string"},
                 "summary": {"type": "string"}, "questions": {"type": "array", "items": {"type": "string"}}},
                ("status", "summary", "questions"))


def capability(ident, description, instructions, refs, properties, required):
    return {"id": ident, "skill_name": ident, "description": description,
            "instructions": instructions,
            "input_schema": schema(properties, required), "output_schema": RESULT,
            "execution": {"kind": "agent", "access": "workspace-write", "network": False},
            "knowledge_refs": refs, "explicit_only": True}


def blueprint():
    common = {"project_root": text_field(), "scene_id": text_field(),
              "variant_id": text_field(), "request": text_field()}
    intro = "先读 [知识索引](../../knowledge/index.md)，按任务加载本轮 reference。"
    fantasy = "references/knowledge/chinese-fantasy-scale.md"
    capabilities = [
        capability("scene-assets", "场景资产主控：证据、设计、静帧提示词和回图审查",
            "# 场景资产主控\n\n" + intro + "\n\n读取 [工作流](../../references/workflow.md) 和"
            " [接口](../../references/interfaces.md)。按剧本/资产表原文核对场景，再提出全剧视觉基准与场景设计卡；"
            "批准后写外部出图提示词，回图必须实际打开审查，操作者批准后才能打包。"
            "中式幻想知识只在项目视觉基准批准且当前场景适用时加载，不默认添加仙宫、人物或超现实规则。"
            "用 scripts/scene_project.py 保存源文件哈希、版本与审批；不调用生图或视频工具。"
            "任何缺失材料、冲突或未批准选择列为待裁决，报告真实文件路径。",
            ["knowledge/index.md", "references/workflow.md", "references/interfaces.md",
             "references/evidence.md", "references/source-notes.md"], common, ("request",)),
        capability("scene-evidence", "核对场景原文、资产表和可选场记的来源与冲突",
            "# 场景证据核对\n\n" + intro + "\n\n读取 [证据规则](../../references/evidence.md)。"
            "用资产表稳定场景 ID 定位剧本原文，列地点、时段、天气、物件、活动空间与连续性事实；"
            "每条事实附 source_refs，推导另列。场记只补镜头线索，不覆盖原文。"
            "有冲突就列双方位置与受影响设计，不自行改写。输出可供设计卡读取的证据记录。",
            ["knowledge/index.md", "references/evidence.md", "references/interfaces.md"],
            common, ("project_root", "scene_id", "request")),
        capability("scene-design", "建立全剧视觉基准与逐场景设计卡",
            "# 场景设计\n\n" + intro + "\n\n读取 [设计规则](../../references/design.md) 与证据。"
            "先区分原文事实、风格板可见观察、推导和创作选择；视觉基准需操作者批准。"
            "逐场景定主空间、活动路线、尺度参照、材料光向、前中后景和连续性不变量。"
            "中式幻想方向已批准时才读 [尺度知识](../../references/knowledge/chinese-fantasy-scale.md)，"
            "源案例的仙人人数、画幅和工具参数不当默认。用 CLI 提交设计卡并等待操作者批准。",
            ["knowledge/index.md", "references/design.md", "references/evidence.md",
             "references/interfaces.md", fantasy], common,
            ("project_root", "scene_id", "request")),
        capability("scene-image-prompt", "从已批准场景卡编写外部静帧提示词",
            "# 场景静帧提示词\n\n" + intro + "\n\n读取 [提示词方法](../../references/prompting.md)"
            "、当前已批准视觉基准与设计卡。参考图逐张标职责；列场景事实、空间主次、活动区域、"
            "尺度、材料光线、不变量和回图检查点。当前场景已批准幻想尺度时才加载专项知识。"
            "输出 ScenePromptPackageV1 并通过 scripts/scene_project.py submit 合同检查；交操作者外部出图。"
            "不写 Midjourney 固定参数，不调用生图 API。",
            ["knowledge/index.md", "references/prompting.md", "references/interfaces.md", fantasy],
            {**common, "target_model": text_field()},
            ("project_root", "scene_id", "request")),
        capability("scene-image-review", "按剧本事实和场景设计审查回流静帧",
            "# 场景图片审查\n\n" + intro + "\n\n必须实际打开回流图，再读取"
            " [审查规则](../../references/review.md)、当前设计卡与剧本证据。"
            "比较地点事实、活动空间、结构连续性、尺度、人物/道具新增和构图。"
            "对无法看清之处标 uncertain；有缺陷标 revise。提交 SceneImageReviewV1，"
            "给可定位的局部返修方向；通过后仍由操作者用 CLI 批准图片。",
            ["knowledge/index.md", "references/review.md", "references/interfaces.md", fantasy],
            {**common, "image_path": text_field()},
            ("project_root", "scene_id", "image_path", "request"))
    ]
    files = {path.relative_to(CONTENT).as_posix(): path.read_text(encoding="utf-8")
             for path in CONTENT.rglob("*") if path.is_file() and
             "__pycache__" not in path.parts and path.suffix != ".pyc"}
    sources = [
        {"origin": "local:刺猬星球/03-宏大中式幻想图像与视频/SKILL.md",
         "revision": "sha256:eda4207aca0d204a9fb2182051465f05a18bf9617ed7db5ab87031e8319e2f8f",
         "license": "not provided", "adaptation": "独立改写场景尺度与空间组织；不复制 Skill 原文"},
        {"origin": "local:刺猬星球/03-宏大中式幻想图像与视频/references/visual-language.md",
         "revision": "sha256:8a417110d55d189e1ad6e5cb12e2acff77cf9c56c3de5607e43e53925f9e8a21",
         "license": "not provided", "adaptation": "把题材专属视觉语法变成条件加载的场景知识"},
        {"origin": "local:刺猬星球/03-宏大中式幻想图像与视频/references/still-prompts.md",
         "revision": "sha256:35a1f7dc18375117745582e115cf03f670e407147cc2d96a1a9da9366cf489d6",
         "license": "not provided", "adaptation": "独立编写外部静帧提示词顺序；舍弃固定人物和工具参数"},
        {"origin": "local:刺猬星球/03-宏大中式幻想图像与视频/references/video-motion.md",
         "revision": "sha256:82b589c1391aaee96aa30633fb15a3a748f025ba1f1f9347299243ca2e63e4ff",
         "license": "not provided", "adaptation": "仅登记后续视频能力候选，不纳入静帧插件"}
    ]
    return {"schema_version": "HarnessBlueprintV1",
            "plugin": {"name": "scene-assets", "version": VERSION,
                       "description": "从剧本证据建立可审查的场景静帧资产和外部出图提示词",
                       "author": {"name": "开宝箱工作室"}},
            "goal": "可独立安装的场景资产子插件，中式幻想尺度为条件知识",
            "acceptance_criteria": ["标准剧本与资产表可追溯", "场景设计与图片逐阶段审批",
                                    "幻想知识条件加载", "图片回流审查阻断无效结果"],
            "open_questions": [], "capabilities": capabilities, "files": files,
            "workflows": [], "sources": sources}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_interface(output: Path) -> None:
    interface = {"displayName": "场景资产插件", "shortDescription": "从剧本依据到场景静帧资产",
                 "longDescription": "场景证据、设计、外部出图提示词与回图审查。",
                 "developerName": "开宝箱工作室", "category": "Productivity",
                 "defaultPrompt": "Use $scene-assets to plan scene assets from my screenplay and asset table."}
    public = output / "plugin.json"
    manifest = json.loads(public.read_text(encoding="utf-8"))
    manifest["version"] = VERSION
    manifest["extensions"]["com.openai"]["interface"] = interface
    public.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local = output / ".codex-plugin" / "plugin.json"
    manifest = json.loads(local.read_text(encoding="utf-8"))
    manifest["version"] = VERSION
    manifest["interface"] = {k: interface[k] for k in
                             ("displayName", "shortDescription", "defaultPrompt")}
    local.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--creator", type=Path, default=ROOT.parent / "harness-creator")
    parser.add_argument("--sync", action="store_true")
    args = parser.parse_args()
    spec = SOURCE / "blueprint.json"
    spec.write_text(json.dumps(blueprint(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "scene-assets"
    if output.exists():
        if not args.sync:
            raise SystemExit(f"Output exists: {output}; use --sync")
        lock = output / "generation-lock.json"
        baseline = json.loads(lock.read_text(encoding="utf-8"))["files"]
        updates = dict(blueprint()["files"])
        updates["harness-blueprint.json"] = spec.read_text(encoding="utf-8")
        updates["sources.lock.json"] = json.dumps(
            {"schema_version": "SourceReceiptsV1", "sources": blueprint()["sources"]},
            ensure_ascii=False, indent=2) + "\n"
        for relative in [*updates, "plugin.json", ".codex-plugin/plugin.json"]:
            target = output / relative
            if target.exists() and sha(target) != baseline.get(relative):
                raise SystemExit(f"User or concurrent edit detected: {relative}")
        for relative, content in updates.items():
            target = output / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        apply_interface(output)
        hashes = {path.relative_to(output).as_posix(): sha(path) for path in output.rglob("*")
                  if path.is_file() and path != lock}
        lock.write_text(json.dumps({"files": hashes}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    else:
        subprocess.run([sys.executable, str(args.creator.resolve() / "harness.py"), "build",
                        "--spec", str(spec), "--output", str(output), "--confirmed"], check=True)
        apply_interface(output)
        names = {"scene-assets": "场景资产主控", "scene-evidence": "场景证据核对",
                 "scene-design": "场景设计", "scene-image-prompt": "场景静帧提示词",
                 "scene-image-review": "场景回图审查"}
        for slug, display in names.items():
            path = output / "skills" / slug / "agents" / "openai.yaml"
            path.write_text(path.read_text(encoding="utf-8").replace(
                f"display_name: {slug}", f"display_name: {display}"), encoding="utf-8")
        lock = output / "generation-lock.json"
        hashes = {path.relative_to(output).as_posix(): sha(path) for path in output.rglob("*")
                  if path.is_file() and path != lock}
        lock.write_text(json.dumps({"files": hashes}, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
