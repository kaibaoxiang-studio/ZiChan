#!/usr/bin/env python3
"""Build the standalone character-assets plugin with Harness Creator."""
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


def schema(properties, required=()):
    return {"type": "object", "properties": properties,
            "required": list(required), "additionalProperties": False}


def text_field():
    return {"type": "string", "minLength": 1}


RESULT = schema({"status": {"type": "string"}, "artifact_path": {"type": "string"},
                 "summary": {"type": "string"}, "questions": {"type": "array", "items": {"type": "string"}}},
                ("status", "summary", "questions"))


def capability(ident, description, instructions, refs, properties, required=()):
    return {"id": ident, "skill_name": ident, "description": description,
            "instructions": instructions,
            "input_schema": schema(properties, required), "output_schema": RESULT,
            "execution": {"kind": "agent", "access": "workspace-write", "network": False},
            "knowledge_refs": refs, "explicit_only": True}


def blueprint():
    refs = "先读 [知识索引](../../knowledge/index.md)，按情景只加载本轮需要的 reference。"
    common = {"project_root": text_field(), "character_id": text_field(),
              "variant_id": text_field(), "request": text_field()}
    capabilities = [
        capability(
            "character-assets", "角色资产主控：从剧本依据到可复用角色资产包",
            "# 角色资产主控\n\n" + refs + "\n\n" +
            "使用 [工作流](../../references/workflow.md) 与 [接口](../../references/interfaces.md)。"
            "先定位用户项目和当前阶段；没有项目时用内置 scripts/character_project.py 导入标准剧本与资产表，场记可选。"
            "从角色清单做第 -1 阶段视觉基准和全员轻规划；主角与重要角色分轮 Grill Me，普通角色分层处理。"
            "每轮只推进一个已授权且依赖已批准的阶段；及时提交结构化 JSON 并通过 CLI 记录批准、图片、审查和来源。"
            "本插件只写 GPT Image 2.5 提示词，不调用生图工具。用户回图后必须实际查看图片，"
            "通过审查与操作者确认后才进入下一阶段。新细节先提议，获批后修改设计卡。"
            "仅在四阶段均通过时打包。运行中报告实际文件路径、未解决疑点与下一步；不虚报成图质量。",
            ["knowledge/index.md", "references/workflow.md", "references/interfaces.md",
             "references/evidence.md", "references/source-notes.md"], common, ("request",)),
        capability(
            "character-evidence", "核对剧本事实、资产表与场记来源并列冲突",
            "# 角色证据核对\n\n" + refs + "\n\n"
            "读取 [证据规则](../../references/evidence.md) 和项目来源文件。"
            "以标准剧本原文为事实基准，资产表只供 ID/层级/状态索引，场记作可选镜头与情绪核对。"
            "逐条分类原文事实、保守推导、未批准提案、已批准选择；每条事实附 source_refs。"
            "若三份输入冲突，给出双方位置和受影响角色/字段，返回待裁决，不替用户改写。"
            "如受上游改版影响，列影响角色与全剧视觉基准是否需重审，再用 CLI 记录影响决议。",
            ["knowledge/index.md", "references/evidence.md", "references/interfaces.md"],
            common, ("project_root", "request")),
        capability(
            "character-design", "建立全剧视觉基准、阵容差异与逐人设计卡",
            "# 角色设计\n\n" + refs + "\n\n"
            "读取 [角色方法](../../references/character-design.md) 和"
            " [服装与形态](../../references/costume-and-morphology.md)。"
            "先依据世界规则提出视觉基准供操作者确认，再建立全员轻规划。重点角色逐轮给有依据的"
            " 2–3 个具体方向；记录已确定、待选和已委托事项，不能把单一画风选择扩大成外貌定稿。"
            "设计卡区分原文事实、推导、参考图提取优点与已批准选择；仅明显换装、年龄或严重外观变化建变体。"
            "非人角色按形态改执行参考板。提交 JSON 草案；未解决项清空后请操作者批准。",
            ["knowledge/index.md", "references/character-design.md",
             "references/costume-and-morphology.md", "references/interfaces.md"],
            common, ("project_root", "request")),
        capability(
            "character-image-prompt", "把已批准设计转成 GPT Image 2.5 分阶段提示词",
            "# 图像提示词\n\n" + refs + "\n\n"
            "读取 [出图规则](../../references/prompting.md) 与当前阶段规则。"
            "只使用已批准设计卡及当前选定图片，标注每张参考图的身份/服装/风格职责。"
            "头像产 2–3 条同设计候选；表情按剧情选 9/16 格且图内写中文标签；"
            "全身图头到脚完整；人形执行表按上正脸/45°半侧脸、下无头放大正面服装/完整背面四格。"
            "非人使用已批准替代布局。输出 CharacterPromptPackageV1 与检查点，经 CLI 合同校验后交操作者外部出图。",
            ["knowledge/index.md", "references/prompting.md", "references/expression.md",
             "references/execution-sheet.md", "references/interfaces.md"],
            {**common, "stage": {"type": "string", "enum": ["avatar", "expression", "full_body", "execution"]}},
            ("project_root", "character_id", "stage", "request")),
        capability(
            "character-image-review", "审查回流图片的剧本事实、身份与版式并产报告",
            "# 回图审查\n\n" + refs + "\n\n"
            "必须实际打开目标图片、已定稿头像及设计卡，读取 [审查规则](../../references/review.md)。"
            "分别检查原文事实、身份不变量、体型/服装/配饰、格位、中文标签和裁切。"
            "人形执行表左下有嘴唇/头发残留就是错误；右上约 45°，右下完整背面。"
            "写 CharacterImageReviewV1，列阻断、待修与可采纳提案；无法看清即 uncertain。"
            "提交报告后由操作者明确选图批准，技能不能替代批准。",
            ["knowledge/index.md", "references/review.md", "references/execution-sheet.md",
             "references/interfaces.md"],
            {**common, "image_path": text_field(), "stage": {"type": "string", "enum": list(("avatar", "expression", "full_body", "execution"))}},
            ("project_root", "image_path", "stage", "request")),
        capability(
            "character-image-edit", "针对回图缺陷编写局部修图指令",
            "# 精确修图\n\n" + refs + "\n\n"
            "读取 [修图方法](../../references/editing.md)、对应设计卡、选定头像、目标图与审查问题。"
            "提示词明确目标格位/区域、唯一改变、保持不变的身份与其他已正确内容、回图核对点。"
            "参考图只借操作者指定的优点。文字标签错字只修对应格，不重画脸；"
            "无头服装格残留头部只修裁切与相邻服装区域。不能承诺像素级保持。"
            "修改图回流后仍走审查与操作者批准；想采纳意外新细节先更新设计卡。",
            ["knowledge/index.md", "references/editing.md", "references/review.md"],
            {**common, "image_path": text_field(), "issue": text_field()},
            ("project_root", "image_path", "issue", "request")),
    ]
    files = {path.relative_to(CONTENT).as_posix(): path.read_text(encoding="utf-8")
             for path in CONTENT.rglob("*") if path.is_file()}
    sources = [
        {"origin": "local:AI角色概念设计课.docx", "revision": "sha256:04ab20e00dd9983964f18f69e57059bdefef43109e8e3c4f94f955e57b72f363", "adaptation": "独立编写设计方法与身份检查规则"},
        {"origin": "local:资产概念knowledge.docx", "revision": "sha256:343a42ab44bc8d84c34d62bb7d3b8c8d30b3c53f3ff199bbae3b47674599cdd7", "adaptation": "提炼表情、变体与 2×2 执行参考板"},
        {"origin": "local:角色概念设计知识库.zip", "revision": "sha256:0f95d6493678ab129047767a80fbfd1c63b207a5e475f26e80424d4d305a277d", "adaptation": "提炼角色设计与一致性检查"},
        {"origin": "local:服装史与造型风格知识库.zip", "revision": "sha256:ed0034c9e4aa857f898872800d85945f46eec0aa73bb9a432da645fef70f9e85", "adaptation": "作为造型检索线索并要求另行核实"},
        {"origin": "local:非人角色与极端体型知识库.zip", "revision": "sha256:98464f8f0e6d6744a5b8063be6ff3a40db7ff33c4f790b7223e958f98fc0e929", "adaptation": "独立编写形态适配规则，移除固定人形假设"},
        {"origin": "https://superiguowai.mfdemo.cn/chaoji/2026/10/20/6ad737b25b707.rar", "revision": "sha256:ef0496aeea3c3c105b23c2de27cb191ed2d8102d47d4e7f6b196ec1c765af18b", "adaptation": "仅研究世界到角色、分轮选择与群像差异的方法；未复制无许可证内容"},
        {"origin": "https://github.com/higgsfield-ai/skills", "revision": "f83af0bc1d937c8119099a11f8ebbf5e6fb99819", "license": "MIT", "adaptation": "独立编写参考图与局部编辑方法；未复制 CLI"},
        {"origin": "https://github.com/kaibaoxiang-studio/script-plugins", "revision": "9110d951e882e3ac89a013f2fea42e142fa08b3f", "adaptation": "沿用现有上游 JSON ID/来源契约，不复制业务代码"},
        {"origin": "https://developers.openai.com/api/docs/guides/image-prompting", "revision": "checked:2026-10-21", "adaptation": "独立编写 GPT Image 2.5 提示词与编辑规则"},
    ]
    return {"schema_version": "HarnessBlueprintV1",
            "plugin": {"name": "character-assets", "version": "0.1.0",
                       "description": "从剧本依据建设可追溯的角色视觉资产包与 GPT Image 2.5 提示词",
                       "author": {"name": "开宝箱工作室"}},
            "goal": "独立运行的角色资产子插件：设计、提示词、回图审查与可复用资产包",
            "acceptance_criteria": ["三份输入和顶层快照契约可接入", "阶段批准和图片回流可恢复",
                                    "错误/冲突阻断发布", "知识按情景加载且来源可追溯"],
            "open_questions": [], "capabilities": capabilities, "files": files,
            "workflows": [], "sources": sources}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def apply_interface(output):
    public = output / "plugin.json"
    manifest = json.loads(public.read_text(encoding="utf-8"))
    interface = {
        "displayName": "角色资产插件", "shortDescription": "从剧本依据到角色视觉资产包",
        "longDescription": "角色设计、GPT Image 2.5 提示词、回图审查与可追溯资产包。",
        "developerName": "开宝箱工作室", "category": "Productivity",
        "defaultPrompt": "Use $character-assets to build a character asset package from my screenplay and asset table."
    }
    manifest["extensions"]["com.openai"]["interface"] = interface
    public.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local = output / ".codex-plugin" / "plugin.json"
    local_manifest = json.loads(local.read_text(encoding="utf-8"))
    local_manifest["interface"] = {key: interface[key] for key in
                                    ("displayName", "shortDescription", "defaultPrompt")}
    local.write_text(json.dumps(local_manifest, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--creator", type=Path, default=ROOT.parent / "harness-creator")
    parser.add_argument("--sync", action="store_true",
                        help="Update authored resources in an existing generated plugin")
    args = parser.parse_args()
    creator = args.creator.resolve()
    spec = SOURCE / "blueprint.json"
    spec.write_text(json.dumps(blueprint(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "character-assets"
    if output.exists():
        if not args.sync:
            raise SystemExit(f"Output exists: {output}; use --sync for authored resources")
        lock = output / "generation-lock.json"
        baseline = json.loads(lock.read_text(encoding="utf-8"))["files"]
        updates = {relative: content for relative, content in blueprint()["files"].items()}
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
        print(output)
        return
    subprocess.run([sys.executable, str(creator / "harness.py"), "build", "--spec", str(spec),
                    "--output", str(output), "--confirmed"], check=True)
    apply_interface(output)
    names = {"character-assets": "角色资产主控", "character-evidence": "角色证据核对",
             "character-design": "角色设计", "character-image-prompt": "角色出图提示词",
             "character-image-review": "角色回图审查", "character-image-edit": "角色精确修图"}
    for slug, display in names.items():
        path = output / "skills" / slug / "agents" / "openai.yaml"
        content = path.read_text(encoding="utf-8").replace(f"display_name: {slug}",
                                                        f"display_name: {display}")
        path.write_text(content, encoding="utf-8")
    lock = output / "generation-lock.json"
    hashes = {path.relative_to(output).as_posix(): sha(path) for path in output.rglob("*")
              if path.is_file() and path != lock}
    lock.write_text(json.dumps({"files": hashes}, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
