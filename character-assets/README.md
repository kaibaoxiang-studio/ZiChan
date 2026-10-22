# 角色资产插件 v0.2.1

独立安装的 Codex 插件。主入口为 `$character-assets`；原有的证据、角色设计、提示词、回图审查和局部修图能力继续保留。0.2.0 新增 **群像差异化总控**与 **10 个专项设计 Skill**，共 17 项能力。它们可单独调用，主入口按实际缺口选用，不要求每个角色走完所有专项。

**0.2.1 小版本更新**：新提交的重点人形设计卡使用 `CharacterDesignCardV2.1`，逐项写出面部、发型、体态、皮肤、服饰剪裁/材质/配色和饰品的可画细节，并展示十专项的实际采纳结果或不启用理由。像“领口和肩部结构清楚，布料自然垂落”这样的概括句不能独自作为定稿。新增《拒绝脸谱化人物设计》知识库的 7 份定点快照，区分角色设计空泛与回图的油光、蜡感或脏糊。**头像默认 3:4 竖版**；只有用户明确指定别的比例时才覆盖。详细规则见[具象设计卡标准](references/design-detail-standard.md)、[真实质感与修图标准](references/render-texture-standard.md)及[接口](references/interfaces.md)。

| 新能力 | 解决的问题 |
| --- | --- |
| `$character-cast-differentiation` | 建同框/近邻比较组，检查五轴矩阵、撞脸与全员美型倾向 |
| `$character-hair-design`、`$character-body-design`、`$character-face-design` | 发型块面、形体体态、五官骨相的具体差异 |
| `$character-face-signature-design`、`$character-skin-design` | 面部记忆点与锁骨以上饰品、真实皮肤肌理 |
| `$character-costume-style-design`、`$character-costume-cut-design` | 服饰款式与剪裁结构各自负责的设计问题 |
| `$character-costume-color-design`、`$character-costume-material-design`、`$character-costume-accessory-design` | 配色、材质、衣身/腰/手饰品 |

总控先保留剧本事实与已批准选择，再以剪影、脸部结构、体型体态、头发块面、服装色块五轴比较最易混淆的角色。普通相貌、年龄和生活痕迹是完整设计，不通过默认丑化配角制造差异。专项只提出待审方案，操作者确认后才写入正式设计卡。背景仍须有明确批准依据。

## 输入与产物

标准化剧本和资产表必需，场记表可选。支持 JSON、Markdown、Excel，优先使用 JSON；也可用顶层 `AssetProjectSnapshotV1` 初始化。文件可以作为聊天附件提供，也可以给绝对路径。项目工作目录保留原件副本、SHA、设计卡、提示词、回流图片、审查与审批。最终 `CharacterAssetPackV1` 只包含对应角色变体的已定稿材料。

新项目建议使用 `CastPlanV2` 与 `CharacterDesignCardV2.1`，记录五轴识别特征、近邻比较和六组具象细节。旧项目的 V1/V2 记录继续可读，已批准角色不因升级自动重设计。`scripts/cast_diff_audit.py` 能列出文本字段重复与待补轴；实际撞脸、真实度和皮肤质感仍需看回流图并排判断。

插件**只写 GPT Image 2.5 提示词**。操作者在外部工具生成图片，回传并逐阶段确认。人形执行资产表上左正脸、上右约 45° 半侧脸；下左是从颈肩以下到鞋的放大无头正面服装主体，下右是从头到鞋的完整背面。非人按设计卡批准的版式适配。

## 安装

保留整个插件目录，使用 Python 3.12+：

```sh
python3 scripts/bootstrap.py --install
python3 harness.py doctor
codex plugin marketplace add /absolute/path/to/character-assets --json
codex plugin add character-assets@zichan-local --json
```

安装后在新聊天选择“角色资产插件”，或输入 `$character-assets`。如果当前聊天尚未刷新已安装 Skill 清单，请开新聊天。插件目录内不放剧本或回流图；让主入口在工作区创建项目目录。

## 首次使用

```text
$character-assets 请用这份标准化剧本和资产表建立角色资产项目；场记表也在附件中。
先给出第 -1 阶段视觉基准与全员轻规划，再从 CHR-001 开始分轮设计。
```

主入口会按 [工作流](references/workflow.md) 使用 `scripts/character_project.py`。想单独审查已有图，可调用 `$character-image-review` 并给出项目目录和图片。需要局部修图提示词，可调用 `$character-image-edit`。结构化 JSON 格式见 [接口](references/interfaces.md)；知识按 [索引](knowledge/index.md) 加载。

10 个专项的输入/输出见 [专项交接](references/specialist-contract.md)，群像审查方法见 [差异化框架](references/differentiation-framework.md)。可对草案运行：

```sh
python3 scripts/cast_diff_audit.py --cast-plan /absolute/cast-plan.json --output /absolute/cast-audit.json
```

`01-通用图片生成` 的方法已转成角色专用的[提示词骨架](references/prompting.md)与[局部修图骨架](references/editing.md)：逐张说明参考图职责、图内中文原样写出、每轮只修一个错误并重新检查整张回流图。来源及 Apache-2.0 许可见 [第三方说明](THIRD_PARTY_NOTICES.md)。

本地 CLI 可直接查看项目：

```sh
python3 scripts/character_project.py status --project-root /absolute/project/directory
```

手动测试材料见 [样例剧本、资产表与验收清单](examples/manual-acceptance.md)；[V2 群像样例](examples/sample-cast-plan-v2.json)可用于差异化审查。

原始课程、用户提供的 12 份知识库 ZIP、旧 Skill ZIP、外部 RAR、剧本和具体人物参考图都不在插件内；本包只有独立改写的规则与来源收据。课程对相貌、体型、颜色和人格的固定映射不作为事实使用。相机型号不会保证实际光学效果，外部去噪与线稿重建须看回图复核。图片审查依赖实际回流图片，结构验证不等同于视觉验收。
