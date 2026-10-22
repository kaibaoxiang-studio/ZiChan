#!/usr/bin/env python3
"""Build the standalone character-assets plugin with Harness Creator."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

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
                ("status", "artifact_path", "summary", "questions"))


SPECIALISTS = [
    ("character-world-appearance-design", "环境与技术外貌设计：世界压力、资源与可达技术", "world-appearance",
     "先核对世界与角色接触证据，再提出能在身体、护理、装备或材料上看到的影响；不得把气候、族群或阶层直接映射成固定五官和人格。"),
    ("character-feature-focus", "特征聚焦：主锚点、安静区与自然不对称", "feature-focus",
     "从剧本处境提炼一句辨识核心；提出少量主锚点与退居次要的特征，核对正侧背可见性、近邻撞型和自然不对称。不得自动添加伤痕或痣。"),
    ("character-hair-design", "发型设计：发流、体积、轮廓与跨视角连续性", "hair",
     "建立发际、发流、发量、前侧后体积和束发结构；与最相近角色比较发型块面，核对生活方式及背面结构。"),
    ("character-body-design", "形体体态设计：年龄比例、骨架、重心与动作习惯", "body",
     "区分骨架、体重分布、比例和重心；先定测量姿态，再给头高/全高的约数及肩胯、同一端点体系的上段/下段、肘腕、膝踝的数值或骨点参照。身高体重和‘修长’不能代替比例；写颅胸盆体块与前侧背一致性，以剧本动作检验关节及衣装余量。"),
    ("character-face-design", "五官面部设计：原创骨相、比例与非模板面孔", "face",
     "组合脸长宽、颧颌、眉眼距、鼻口比例，提出可画且原创的面孔；与比较组并排防撞脸，不用五官推断人格。"),
    ("character-face-signature-design", "面部记忆点与锁骨以上饰品设计", "face-memory",
     "先用已有结构识别，再考虑面部记号、发饰、耳饰和颈饰；写固定点与连续性，新增伤痕纹身必须待批准。"),
    ("character-face-decoration-design", "面部装饰与妆容设计：稳定、施加与临时状态", "face-decoration",
     "按稳定原生痕迹、主动施加的妆面和临时状态分层；每项写位置、形态、叙事依据和起止状态，无需求可不设计。"),
    ("character-skin-design", "皮肤肌理设计：年龄、环境与真实表面", "skin",
     "写自然毛孔、局部光泽、纹理、色沉及有依据的生活痕迹；区分稳定肌理与临时污损，避免磨皮。"),
    ("character-costume-style-design", "服饰款式设计：衣装品类、长度和层次", "costume-style",
     "从世界、场合、职业与行动决定衣装品类和整体轮廓；不侵占剪裁、配色、材质与饰品职责。"),
    ("character-costume-cut-design", "服饰剪裁设计：结构线、连接与活动余量", "costume-cut",
     "在选定款式上解决肩线、领口、袖、腰、摆、褶与闭合；让前侧背结构一致且动作可行。"),
    ("character-costume-color-design", "服饰配色设计：明度、饱和度与群像色块", "costume-color",
     "在项目色域内分配主辅点色与部位面积，比较同框角色色块；不把色彩心理当人格事实。"),
    ("character-costume-material-design", "服饰材质设计：重量、光泽、垂坠与磨损", "costume-material",
     "为各衣层写材料及物理表现，检查气候、行动、资源和制作技术相容，拒绝统一塑料感。"),
    ("character-costume-accessory-design", "服饰饰品设计：衣身、腰、手与随身穿戴物", "costume-accessory",
     "处理锁骨以下饰品的功能、固定、重量与道具 ID；跨锁骨物件与面部饰品专项只指定一个主责。"),
]


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
            "先用 [需求路由与整合](../../references/routing-and-integration.md) 标定单张或批量范围、当前状态与前置门槛。"
            "先定位用户项目和当前阶段；没有项目时用内置 scripts/character_project.py 导入标准剧本与资产表，场记可选。"
            "从角色清单做第 -1 阶段视觉基准和全员轻规划；用群像差异化总控建立比较组与五轴矩阵，"
            "先形成逐人专项路由，再对特征焦点、发型、体型、五官、皮肤和服饰按缺口实际调用专项；每个 used 项保存有效提案和所选方案。"
            "提交重点人形卡必须写清脸、发、三维体块、皮肤、服饰和饰件的可画细节；身体要有头身数值与其余骨点参照，不能只写身高体重或修长。列十三专项的采纳结果或不启用理由，并记录环境技术影响与面部表面状态。"
            "主角与重要角色分轮 Grill Me，普通角色分层处理；已批准角色不因新方法自动重做。"
            "每轮只推进一个已授权且依赖已批准的阶段；及时提交结构化 JSON 并通过 CLI 记录批准、图片、审查和来源。"
            "本插件只写 GPT Image 2.5 提示词，不调用生图工具。用户回图后必须实际查看图片，"
            "通过审查与操作者确认后才进入下一阶段。新细节先提议，获批后修改设计卡。"
            "头像默认 3:4 竖版，全身图默认 9:16 竖版，只有操作者明确要求才更改。"
            "人形头像与表情以脸为主体，可取完整头部、双肩及上胸，不固定裁到锁骨以上；服装不入画用 face_only，上胸入画用对应白色背心，整组模式一致；"
            "全身图用白色背心、短裤、赤脚作模卡参考，执行资产表恢复已批准正式服装。"
            "新项目依次完成头像、九宫格、全身模卡、每状态服饰设计图、执行资产图；每张图按资产名命名，逐图通过后才打包。旧项目沿用原四阶段。运行中报告实际文件路径、未解决疑点与下一步；不虚报成图质量。",
            ["knowledge/index.md", "references/workflow.md", "references/interfaces.md",
             "references/routing-and-integration.md", "references/costume-design-stage.md",
             "references/model-card-baseline.md",
             "references/evidence.md", "references/source-notes.md",
             "references/differentiation-framework.md", "references/specialist-contract.md",
            "references/design-detail-standard.md", "references/render-texture-standard.md",
            "references/feature-focus-and-body-form.md"],
            {**common, "mode": {"type": "string", "enum": ["single", "batch"]},
             "character_ids": {"type": "array", "items": text_field()},
             "variant_ids": {"type": "array", "items": text_field()},
             "target_stages": {"type": "array", "items": {"type": "string", "enum":
                                ["avatar", "expression", "full_body", "costume_design", "execution"]}}},
            ("request",)),
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
            "先由世界环境与技术专项给出可见的环境/技术影响，再按缺口路由面部装饰与妆容专项；两者都须有角色证据或批准。"
            "先依据世界规则提出视觉基准供操作者确认，再调用群像差异化总控建立全员轻规划。"
            "重点角色逐轮给有依据的"
            " 2–3 个具体方向；记录已确定、待选和已委托事项，不能把单一画风选择扩大成外貌定稿。"
            "默认检查发型、体型、五官是否落入全员美型模板；按实际缺口加载对应专项知识，"
            "近邻角色并排比较，保留普通相貌和真实皮肤的可能。"
            "先写可复核的专项路由；按具象标准把十三专项的已采用结果或不启用理由写入设计稿，used 必须提交真实提案文件及被选方案。"
            "新项目重点人形卡用 CharacterDesignCardV2.4，记录世界影响、面部表面层、特征主次、自然不对称决定与五组身体比例锚点。"
            "设计卡区分原文事实、推导、参考图提取优点与已批准选择；仅明显换装、年龄或严重外观变化建变体。"
            "非人角色按形态改执行参考板。提交 JSON 草案；未解决项清空后请操作者批准。",
            ["knowledge/index.md", "references/character-design.md",
             "references/costume-and-morphology.md", "references/interfaces.md",
             "references/differentiation-framework.md", "references/specialist-contract.md",
             "references/design-detail-standard.md", "references/feature-focus-and-body-form.md",
             "references/routing-and-integration.md",
             "references/knowledge/character-world-appearance-design/world-appearance.md",
             "references/knowledge/character-face-decoration-design/face-decoration.md",
             "references/knowledge/character-design/feature-focus-design.md",
             "references/knowledge/character-design/anti-stereotype-texture.md"],
            common, ("project_root", "request")),
        capability(
            "character-image-prompt", "把已批准设计转成 GPT Image 2.5 分阶段提示词",
            "# 图像提示词\n\n" + refs + "\n\n"
            "读取 [出图规则](../../references/prompting.md) 与当前阶段规则。"
            "先检查已批准卡是否具象，空泛则回设计轮补细；按真实质感规则选择适量可见肌理和材料词。"
            "只使用已批准设计卡及当前选定图片，按画幅抽取主锚点，标注每张参考图的身份/服装/风格职责。"
            "背景也是设计维度：无明确批准时仅用无场景、无纹理的中性底色作核对背景；"
            "不得自行加入地点、建筑、地貌、天气或借光线描述暗示剧情场景。"
            "头像默认 3:4 竖版且每条提示词写明比例，只有操作者明确指定才覆盖；产 2–3 条同设计候选；"
            "人形头像与表情以脸为主体，可取完整头部、双肩及上胸，不固定裁到锁骨以上；服装不入画用 face_only，上胸入画用对应白色背心，整组模式一致；新项目默认九宫格并写中文标签，16 格须有用户明确要求；"
            "全身图默认 9:16 竖版，每条提示词与验收项写明比例，穿对应白色背心、短裤并赤脚，头到双脚完整并留边界，逐条继承已批准设计卡中的头身、肩胯与腿身关系并核对；"
            "九宫格和全身模卡批准后，每个状态先做独立服饰设计图并批准；执行表必须引用该状态服饰图，按上正脸/45°半侧脸、下无头放大正面服装/完整背面四格。"
            "非人使用已批准替代布局。输出 CharacterPromptPackageV1 与检查点，经 CLI 合同校验后交操作者外部出图。",
            ["knowledge/index.md", "references/prompting.md", "references/model-card-baseline.md", "references/expression.md",
             "references/execution-sheet.md", "references/costume-design-stage.md", "references/interfaces.md",
             "references/design-detail-standard.md", "references/render-texture-standard.md",
             "references/knowledge/character-image-prompt/feature-focus-prompt.md",
             "references/knowledge/character-image-prompt/hedgehog-2d3d.md",
             "references/knowledge/character-image-prompt/hedgehog-general-image-skill.md",
             "references/knowledge/character-image-prompt/anti-stereotype-texture.md"],
            {**common, "stage": {"type": "string", "enum": ["avatar", "expression", "full_body", "costume_design", "execution"]}},
            ("project_root", "character_id", "stage", "request")),
        capability(
            "character-image-review", "审查回流图片的剧本事实、身份与版式并产报告",
            "# 回图审查\n\n" + refs + "\n\n"
            "必须实际打开目标图片、已定稿头像及设计卡，读取 [审查规则](../../references/review.md)。"
            "分别检查原文事实、身份不变量、体型/服装/配饰、格位、中文标签、裁切与背景依据。"
            "头像查默认 3:4，全身图查最终像素比例 9:16 与完整头手脚；服饰设计图逐状态核对衣装结构与妆面连续性，执行图核对同状态服饰锚点。"
            "按当前视角检查批准的主锚点与三维比例，分辨设计卡空泛与回图失真，查看油光、自然肌理、材质层次与伪影。"
            "人形执行表左下有嘴唇/头发残留就是错误；右上约 45°，右下完整背面。"
            "写 CharacterImageReviewV1，列阻断、待修与可采纳提案；无法看清即 uncertain。"
            "提交报告后由操作者明确选图批准，技能不能替代批准。",
            ["knowledge/index.md", "references/review.md", "references/model-card-baseline.md", "references/execution-sheet.md",
             "references/interfaces.md", "references/render-texture-standard.md", "references/costume-design-stage.md",
             "references/knowledge/character-image-review/feature-focus-review.md",
             "references/knowledge/character-image-review/anti-stereotype-texture.md"],
            {**common, "image_path": text_field(), "stage": {"type": "string", "enum": list(("avatar", "expression", "full_body", "costume_design", "execution"))}},
            ("project_root", "image_path", "stage", "request")),
        capability(
            "character-image-edit", "针对回图缺陷编写局部修图指令",
            "# 精确修图\n\n" + refs + "\n\n"
            "读取 [修图方法](../../references/editing.md)、对应设计卡、选定头像、目标图与审查问题。"
            "提示词明确目标格位/区域、唯一改变、保持不变的身份与其他已正确内容、回图核对点。"
            "参考图只借操作者指定的优点。文字标签错字只修对应格，不重画脸；"
            "无头服装格残留头部只修裁切与相邻服装区域。不能承诺像素级保持。"
            "修改图回流后仍走审查与操作者批准；想采纳意外新细节先更新设计卡。",
            ["knowledge/index.md", "references/editing.md", "references/review.md",
             "references/render-texture-standard.md",
             "references/knowledge/character-image-edit/hedgehog-general-image-prompting.md",
             "references/knowledge/character-image-edit/anti-stereotype-texture.md"],
            {**common, "image_path": text_field(), "issue": text_field()},
            ("project_root", "image_path", "issue", "request")),
    ]
    capabilities.append(capability(
        "character-cast-differentiation", "群像差异化总控：比较组、五轴矩阵与回图防撞型复核",
        "# 群像差异化总控\n\n读取 [差异化框架](../../references/differentiation-framework.md)、"
        "[专项交接](../../references/specialist-contract.md) 和群像知识快照。"
        "从真实同框及功能近邻建立比较组，生成角色 × 识别轴矩阵；指出重复的结构组合和全员美型偏差。"
        "按文本阶段或已收到的图片明确证据等级；需要回图判断时实际打开图片。"
        "不能因差异化硬造疤痕、怪发或极端体型，不自动改已批准卡。"
        "把类型标签翻译成可画结构，分别报告设计空泛与回图渲染趋同。"
            "给主控具体修订点与应启用的专项，检查各角色主锚点是否同质化；问题经操作者选择后才写入正式设计卡。",
        ["knowledge/index.md", "references/differentiation-framework.md",
         "references/specialist-contract.md",
         "references/knowledge/character-cast-differentiation/ensemble.md",
         "references/knowledge/character-cast-differentiation/legacy-visual.md",
         "references/knowledge/character-cast-differentiation/anti-stereotype-texture.md"],
        {**common, "cast_plan_path": text_field(), "comparison_group": {"type": "array", "items": text_field()}},
        ("project_root", "request")))
    for ident, description, source_id, method in SPECIALISTS:
        extra_refs = (["references/render-texture-standard.md",
                       f"references/knowledge/{ident}/anti-stereotype-texture.md"]
                      if ident in {"character-skin-design", "character-costume-material-design"} else [])
        specialist_refs = [f"references/knowledge/{ident}/{source_id}.md"]
        if ident == "character-body-design":
            specialist_refs.append("references/knowledge/character-body-design/body-proportion-3d.md")
        if ident == "character-feature-focus":
            specialist_refs.append("references/feature-focus-and-body-form.md")
        capabilities.append(capability(
            ident, description,
            "# " + description + "\n\n读取 [专项交接](../../references/specialist-contract.md)、"
            "[群像差异化框架](../../references/differentiation-framework.md) 与本专项知识快照。"
            + method + "读取已批准视觉基准、当前设计卡与比较组；输出有依据的 2–3 个可见方案，"
            "每方案列至少两个部位、形状、位置/连接和依据明确的设计元素，供设计卡实际采纳；"
            "明确原文事实、创作提案、制作核对点及与近邻的差异。"
            "新特征只能作为待选方案，不能代替操作者批准。"
            "提案包含当前 variant_id；提交 CharacterSpecialistProposalV1.1 JSON 与短 Markdown，运行 scripts/validate_specialist_proposal.py；不调用生图。",
            ["knowledge/index.md", "references/specialist-contract.md",
             "references/differentiation-framework.md", "references/design-detail-standard.md",
             *specialist_refs, *extra_refs],
            common, ("project_root", "character_id", "request")))
    files = {path.relative_to(CONTENT).as_posix(): path.read_text(encoding="utf-8")
             for path in CONTENT.rglob("*") if path.is_file() and
             "__pycache__" not in path.parts and path.suffix != ".pyc"}
    adoption = json.loads((SOURCE / "knowledge-adoption.json").read_text(encoding="utf-8"))
    files["knowledge/archive-manifest.json"] = json.dumps(adoption, ensure_ascii=False, indent=2) + "\n"
    lock = json.loads(files["knowledge-lock.json"])
    for item in adoption["sources"]:
        rule = (SOURCE / item["rules"]).read_text(encoding="utf-8")
        relative = f'references/knowledge/{item["capability"]}/{item["id"]}.md'
        rendered = (f'<!-- source-id: {item["id"]}; revision: {item["ingested_sha256"]} -->\n'
                    + rule)
        files[relative] = rendered
        lock["snapshots"] = [x for x in lock["snapshots"] if x["path"] != relative]
        lock["snapshots"].append({
            "source_id": item["id"], "source_sha256": item["ingested_sha256"],
            "origin": "local:" + item["archive"], "path": relative,
            "rules_sha256": hashlib.sha256(rendered.encode()).hexdigest(),
            "capability_ids": [item["capability"]]})
    files["knowledge-lock.json"] = json.dumps(lock, ensure_ascii=False, indent=2) + "\n"
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
        {"origin": "local:刺猬星球素材/3d角色质感提示词/2d转3d提示词.txt", "revision": "sha256:6faa60a3f7b37e46d2ae4401d2f83729887deba031c2619bb87d3d3ea210b7fa", "adaptation": "独立编写可选的媒介转换知识快照；保留身份与服装"},
        {"origin": "local:刺猬星球素材/3d角色质感提示词/替换海报角色提示词.txt", "revision": "sha256:ec94b106196958c3d25332d07547192c9aec5d2eb7a6733aab9cece7ca779a79", "adaptation": "参考图职责分离；换装需要变体批准"},
        {"origin": "local:刺猬星球素材/动漫PV角色概念设计/SKILL.md", "revision": "sha256:bf266f8942438273ead0e2d6fe1a26b9988e2dfaecd12b5b15eb48417975ae11", "adaptation": "独立提炼风格与角色细节分离以及回图局部诊断"},
        {"origin": "local:刺猬星球素材/打斗提示词/四视图提示词.txt", "revision": "sha256:b750b10de906df64261ff823baf9f236077711eff4c8798efe68adcd27cef7d2", "adaptation": "对照已有执行参考板合同；只保留差异审查记录"},
        {"origin": "local:刺猬星球素材/01-通用图片生成/SKILL.md", "revision": "sha256:3e8fdab2d0c0b69d121503a2d2833a067a672afca21b51c5e1ac99a1f30860fb", "license": "Apache-2.0", "adaptation": "改写角色提示词结构与参考图职责；不携带生图 API/CLI"},
        {"origin": "local:刺猬星球素材/01-通用图片生成/references/prompting.md", "revision": "sha256:d957a45cb24fe2cf1a85858674fc533f15a5f4621355f559a13a93168999c2dd", "license": "Apache-2.0", "adaptation": "改写单项修图与全图复核方法；保留外部出图"},
    ]
    sources += [{"origin": "local:" + item["archive"],
                 "revision": "sha256:" + item["archive_sha256"],
                 "adaptation": "用户课程方法精炼为 " + item["capability"] +
                 " 的独立规则；未打包原文，原始成员哈希见 knowledge/archive-manifest.json"}
                for item in adoption["sources"]]
    return {"schema_version": "HarnessBlueprintV1",
            "plugin": {"name": "character-assets", "version": "0.2.4.1",
                       "description": "从剧本依据建设可追溯的角色视觉资产包与 GPT Image 2.5 提示词",
                       "author": {"name": "开宝箱工作室"}},
            "goal": "独立运行的角色资产子插件：设计、提示词、回图审查与可复用资产包",
            "acceptance_criteria": ["三份输入和顶层快照契约可接入", "阶段批准和图片回流可恢复",
                                    "错误/冲突阻断发布", "知识按情景加载且来源可追溯",
                                    "群像比较组识别发型、体型和面孔模板化", "专项只按缺口启用且不改已批准卡",
                                    "新重点人形卡交世界影响、面部状态、可追溯比例锚点与十三专项覆盖", "used 专项有真实提案及所选方案哈希交接",
                                    "头像默认 3:4、全身图默认 9:16，且仅明确用户要求可覆盖",
                                    "人形头像以脸为主体，允许头肩至上胸取景；服装不入画用 face_only，上胸入画用对应白色背心，表情继承模式；全身图采用背心短裤赤脚模卡，执行表恢复正式服装",
                                    "五阶段单张和批量任务按资产状态、依赖和批准流转，图片文件名包含资产名",
                                    "去油与噪点修复区分设计和渲染证据"],
            "open_questions": [], "capabilities": capabilities, "files": files,
            "workflows": [], "sources": sources}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def finalize_output(output):
    apply_interface(output)
    # Harness Creator currently validates only three-part versions. Codex accepts
    # the requested four-part patch version, so keep the final runtime validator
    # aligned with the published manifest after the staged build completes.
    validator = output / "runtime" / "harness_core" / "packages.py"
    source = validator.read_text(encoding="utf-8")
    old = r"r'\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?'"
    new = r"r'\d+\.\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9.-]+)?'"
    if old not in source:
        raise RuntimeError("Harness Creator version validator changed; review version compatibility")
    validator.write_text(source.replace(old, new, 1), encoding="utf-8")
    names = {"character-assets": "角色资产主控", "character-evidence": "角色证据核对",
             "character-design": "角色设计", "character-image-prompt": "角色出图提示词",
             "character-image-review": "角色回图审查", "character-image-edit": "角色精确修图",
             "character-cast-differentiation": "角色群像差异化"}
    names.update({ident: description.split("：", 1)[0]
                  for ident, description, _, _ in SPECIALISTS})
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


def apply_interface(output):
    public = output / "plugin.json"
    manifest = json.loads(public.read_text(encoding="utf-8"))
    version = blueprint()["plugin"]["version"]
    interface = {
        "displayName": "角色资产插件", "shortDescription": "从剧本依据到角色视觉资产包",
        "longDescription": "角色设计、GPT Image 2.5 提示词、回图审查与可追溯资产包。",
        "developerName": "开宝箱工作室", "category": "Productivity",
        "defaultPrompt": "Use $character-assets to build a character asset package from my screenplay and asset table."
    }
    manifest["extensions"]["com.openai"]["interface"] = interface
    manifest["version"] = version
    public.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    local = output / ".codex-plugin" / "plugin.json"
    local_manifest = json.loads(local.read_text(encoding="utf-8"))
    local_manifest["version"] = version
    local_manifest["interface"] = {key: interface[key] for key in
                                    ("displayName", "shortDescription", "defaultPrompt")}
    local.write_text(json.dumps(local_manifest, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--creator", type=Path, default=ROOT.parent / "harness-creator")
    parser.add_argument("--sync", action="store_true",
                        help="Update authored resources in an existing generated plugin")
    parser.add_argument("--rebuild", action="store_true",
                        help="Rebuild all capabilities from authored sources after checking the generated lock")
    args = parser.parse_args()
    creator = args.creator.resolve()
    spec = SOURCE / "blueprint.json"
    spec.write_text(json.dumps(blueprint(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    output = ROOT / "character-assets"
    if args.rebuild:
        if output.exists():
            baseline = json.loads((output / "generation-lock.json").read_text(encoding="utf-8"))["files"]
            current = {path.relative_to(output).as_posix(): sha(path) for path in output.rglob("*")
                       if path.is_file() and path.name != "generation-lock.json"
                       and path.suffix != ".pyc" and "__pycache__" not in path.parts}
            if current != baseline:
                changed = sorted(key for key in set(current) | set(baseline)
                                 if current.get(key) != baseline.get(key))
                raise SystemExit(f"Generated plugin has user or concurrent edits: {changed}")
        (ROOT / ".harness").mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="character-rebuild-", dir=ROOT / ".harness") as temp:
            temp = Path(temp)
            stage = temp / "character-assets"
            # Creator's build copies its own licenses/ after authored files. Keep
            # authored notices/licenses out of that initial copy, then overlay
            # every authored file and restore the full source blueprint.
            staged_spec = json.loads(spec.read_text(encoding="utf-8"))
            # The generated bundle is rewritten to the exact requested version
            # in apply_interface() after Harness Creator's initial validation.
            version_parts = staged_spec["plugin"]["version"].split(".")
            if len(version_parts) == 4 and all(part.isdigit() for part in version_parts):
                staged_spec["plugin"]["version"] = ".".join(version_parts[:3]) + "-" + version_parts[3]
            staged_spec["files"] = {key: value for key, value in staged_spec["files"].items()
                                    if not key.startswith("licenses/") and key != "THIRD_PARTY_NOTICES.md"}
            stage_spec_path = temp / "build-spec.json"
            stage_spec_path.write_text(json.dumps(staged_spec, ensure_ascii=False, indent=2) + "\n",
                                       encoding="utf-8")
            subprocess.run([sys.executable, str(creator / "harness.py"), "build", "--spec", str(stage_spec_path),
                            "--output", str(stage), "--confirmed"], check=True)
            for relative, content in blueprint()["files"].items():
                target = stage / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
            (stage / "harness-blueprint.json").write_text(spec.read_text(encoding="utf-8"),
                                                         encoding="utf-8")
            finalize_output(stage)
            backup = temp / "previous"
            if output.exists():
                output.rename(backup)
            try:
                stage.rename(output)
            except Exception:
                if backup.exists():
                    backup.rename(output)
                raise
        print(output)
        return
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
    finalize_output(output)
    print(output)


if __name__ == "__main__":
    main()
